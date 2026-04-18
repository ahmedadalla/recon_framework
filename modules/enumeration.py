import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from config import TEMP_DIR, RESULTS_DIR, WORDLIST, RESOLVERS
from core.discord_alert import send_alert

try:
    import requests
except ImportError:
    requests = None

# 🔹 Build passive commands
def build_commands(domain, temp_dir: Path | None = None):
    temp_root = Path(temp_dir) if temp_dir is not None else TEMP_DIR
    return {
        "subfinder": ["subfinder", "-d", domain, "-o", str(temp_root / f"{domain}_subfinder.txt")],
        "subenum": ["subenum", "-d", domain, "-o", str(temp_root / f"{domain}_subenum.txt")],
        "oneforall": ["oneforall", "--target", domain, "--path", f'{str(temp_root)}', "--fmt", "json", "run"]
    }

def run_tool(task): 
    domain, name, cmd = task 
    print(f"[+] {name} started on {domain}") 
    try: 
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900) 
        print(f"[✓] {name} done on {domain}") 
        return {"domain": domain, "tool": name, "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode} 
    except subprocess.TimeoutExpired:
        print(f"[!] {name} timed out on {domain}, skipping...")
        return {"domain": domain, "tool": name, "stdout": "", "stderr": "timeout", "returncode": 124}
    except Exception as e: 
        return {"domain": domain, "tool": name, "stdout": "", "stderr": str(e), "returncode": -1}

# 🔹 Passive: crt.sh
def get_subdomains(domain, exclude_www=False):
    if requests is None:
        print("[!] requests is not installed. Skipping crt.sh lookup.")
        return []

    url = f"https://crt.sh/?q=%25.{domain}&output=json"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        subdomains = set()
        for entry in data:
            name_value = entry.get("name_value", "")
            for sub in name_value.split("\n"):
                sub = sub.strip().lower()
                if not sub.startswith("*.") and sub.endswith("." + domain):
                    subdomains.add(sub)
        return sorted(subdomains)
    except Exception as e:
        print(f"[!] crt.sh error for {domain}: {e}")
        return []

# 🔹 Active: Puredns Bruteforce
def run_puredns(target, wordlist, temp_dir: Path | None = None):
    print(f"[+] Active DNS Bruteforce (puredns) started on {target}...")
    temp_root = Path(temp_dir) if temp_dir is not None else TEMP_DIR
    output_txt = temp_root / f"{target}_puredns.txt"
    cmd = [
        "puredns", "bruteforce", wordlist, target,
        "-r", RESOLVERS,
        "-w", str(output_txt),
        "--quiet"
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1200)
    except subprocess.TimeoutExpired:
        print(f"[!] puredns timed out for {target}, continuing...")
    print(f"[✓] puredns done for {target}")

# 🔹 Active: Permutations (dnsgen + puredns)
def run_permutations(input_file, temp_dir: Path | None = None):
    print("\n[+] Generating & resolving permutations (dnsgen + puredns)...")
    temp_root = Path(temp_dir) if temp_dir is not None else TEMP_DIR
    perm_output = temp_root / "permutations_resolved.txt"
    cmd = f"dnsgen {input_file} | puredns resolve -r {RESOLVERS} -w {perm_output} --quiet"
    try:
        subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL, timeout=1200)
    except subprocess.TimeoutExpired:
        print("[!] Permutation resolution timed out, continuing with collected data...")
    print("[✓] Permutations resolved")


# 🔹 THIS IS THE MAIN FUNCTION CALLED BY main.py
def run_subdomain_enum(domain, recursive=False, max_workers=5, temp_dir: Path | None = None, results_dir: Path | None = None):
    print(f"\n[=== PHASE 1: SUBDOMAIN ENUMERATION for {domain} ===]")
    temp_root = Path(temp_dir) if temp_dir is not None else TEMP_DIR
    results_root = Path(results_dir) if results_dir is not None else RESULTS_DIR
    master_subs_file = results_root / "master_subdomains.txt"
    master_subs_file.parent.mkdir(parents=True, exist_ok=True)

    tasks = []
    for name, cmd in build_commands(domain, temp_root).items():
        tasks.append((domain, name, cmd))

    # --- 1. PASSIVE GATHERING ---
    print("\n[+] Running Passive Recon...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(run_tool, task) for task in tasks]
        
        for future in as_completed(futures):
            res = future.result()
            if res["tool"] == "oneforall":
                json_file = temp_root / f"{res['domain']}.json"
                if json_file.exists():
                    try:
                        with open(json_file, "r") as f:
                            data = json.load(f)
                        subdomains = set([entry.get("subdomain") for entry in data if entry.get("subdomain")])
                        with open(temp_root / f"{res['domain']}_oneforall.txt", "w") as f:
                            for sub in sorted(subdomains): f.write(sub + "\n")
                    except Exception: pass

    # Run crt.sh with a hard upper bound so this phase cannot hang.
    print("[+] Fetching from crt.sh...")
    crt_subdomains = []
    with ThreadPoolExecutor(max_workers=1) as executor:
        future_crt = executor.submit(get_subdomains, domain)
        try:
            crt_subdomains = future_crt.result(timeout=30)
        except Exception:
            print(f"[!] crt.sh fetch timed out for {domain}, continuing...")

    with open(temp_root / "cert_sh.txt", "w") as f:
        for sub in crt_subdomains:
            f.write(sub + "\n")

    # Merge passive results into the MASTER list
    print("[+] Merging passive results to master list...")
    subprocess.run(f"cat {temp_root}/*.txt | anew {master_subs_file} > /dev/null", shell=True)

    # --- 2. ACTIVE DNS BRUTEFORCING ---
    print("\n[+] Running Active Bruteforcing...")
    run_puredns(domain, WORDLIST, temp_root)
    subprocess.run(f"cat {temp_root}/*_puredns.txt | anew {master_subs_file} > /dev/null 2>&1", shell=True)

    # --- 3. DNS RESOLUTION & PERMUTATIONS ---
    print("\n[+] Running Resolution & Permutations...")
    resolved_file = temp_root / "resolved_master.txt"
    subprocess.run(["dnsx", "-l", str(master_subs_file), "-silent", "-o", str(resolved_file)])

    #run_permutations(resolved_file)
    #subprocess.run(f"cat {TEMP_DIR}/permutations_resolved.txt | anew {master_subs_file} > /dev/null 2>&1", shell=True)

    # --- 4. RECURSIVE ENUMERATION (OPTIONAL) ---
    if recursive:
        print("\n[+] Running RECURSIVE ENUMERATION (This may take a while)...")
        with open(resolved_file, 'r') as f:
            recursive_targets = [line.strip() for line in f if line.strip()]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(run_puredns, target, WORDLIST) for target in recursive_targets]
            for future in as_completed(futures):
                future.result()
        
        subprocess.run(f"cat {temp_root}/*_puredns.txt | anew {master_subs_file} > /dev/null 2>&1", shell=True)

    # --- FINAL RESOLUTION ---
    final_resolved = results_root / "final_resolved_subdomains.txt"
    subprocess.run(["dnsx", "-l", str(master_subs_file), "-silent", "-o", str(final_resolved)])

    if final_resolved.exists():
        count = sum(1 for _ in open(final_resolved))
        send_alert("Phase 1 Complete: Enumeration", f"Found **{count}** live resolved subdomains for {domain}.", 0x2ecc71)
        print(f"[✓] Total Live Subdomains: {count}")

    return final_resolved
