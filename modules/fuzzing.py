import subprocess
import shutil
from pathlib import Path
from urllib.parse import urlparse
from config import RESULTS_DIR
from core.discord_alert import send_alert


def _tool_args(config: dict | None, tool_name: str) -> list[str]:
    if not isinstance(config, dict):
        return []
    tool_args = config.get("tools", {}).get("tool_args", config.get("tool_args", {}))
    value = tool_args.get(tool_name, []) if isinstance(tool_args, dict) else []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def run_fuzzing(live_web_file, config: dict | None = None):
    print("\n[+] Starting Directory Fuzzing (ffuf)...")
    fuzzing_dir = RESULTS_DIR / "fuzzing"
    fuzzing_dir.mkdir(exist_ok=True)
    
    wordlist = "/home/seclinux/mytools/common.txt"
    if isinstance(config, dict):
        configured = config.get("fuzzing", {}).get("wordlist")
        if configured:
            wordlist = str(configured)

    if not Path(live_web_file).exists() or Path(live_web_file).stat().st_size == 0:
        print("[!] No live web targets found. Skipping fuzzing.")
        return fuzzing_dir

    if not Path(wordlist).exists():
        print(f"[!] Wordlist not found: {wordlist}. Skipping fuzzing.")
        return fuzzing_dir

    if not shutil.which("ffuf"):
        print("[!] ffuf binary not found in PATH. Skipping fuzzing.")
        return fuzzing_dir
    
    ffuf_extra = _tool_args(config, "fuzzing")
    urls = [
        line.strip()
        for line in Path(live_web_file).read_text(encoding="utf-8", errors="ignore").splitlines()
        if line.strip()
    ]
    failure_count = 0

    for url in urls:
        parsed = urlparse(url)
        host = parsed.netloc
        if not host:
            continue

        output_file = fuzzing_dir / f"{host}.json"
        base_url = url.rstrip("/")
        cmd = [
            "ffuf",
            "-u",
            f"{base_url}/FUZZ",
            "-w",
            str(wordlist),
            "-mc",
            "200,301,403",
            "-ac",
            "-s",
            "-noninteractive",
            "-of",
            "json",
            "-o",
            str(output_file),
            *ffuf_extra,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            failure_count += 1
            print(f"[!] ffuf failed for {url} (exit code {result.returncode})")

    if failure_count:
        print(f"[!] Fuzzing completed with {failure_count} failed target(s).")
    
    send_alert("Phase Complete: Fuzzing", "Directory fuzzing finished.", 0x9b59b6)
    return fuzzing_dir
