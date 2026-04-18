import re
import os
import shutil
import subprocess
from pathlib import Path
from config import RESULTS_DIR, TEMP_DIR
from core.discord_alert import send_alert
from core.discord_alert import stream_command_with_alerts


def _resolve_httpx_binary():
    env_bin = os.getenv("RECON_HTTPX_BIN", "").strip()
    if env_bin:
        preferred = Path(env_bin)
        if preferred.exists() and preferred.is_file():
            return str(preferred)
    return shutil.which("httpx")


def _tool_args(config: dict | None, tool_name: str) -> list[str]:
    if not isinstance(config, dict):
        return []
    tool_args = config.get("tools", {}).get("tool_args", config.get("tool_args", {}))
    value = tool_args.get(tool_name, []) if isinstance(tool_args, dict) else []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def run_port_scan(input_file, config: dict | None = None, results_dir: Path | None = None):
    print("\n[+] Running Port Scan (nmap)...")
    results_root = Path(results_dir) if results_dir is not None else RESULTS_DIR
    ports_output = results_root / "open_ports.txt"
    ports_output.parent.mkdir(parents=True, exist_ok=True)

    if not input_file.exists() or input_file.stat().st_size == 0:
        print("[!] No resolved subdomains found. Skipping nmap scan.")
        ports_output.touch(exist_ok=True)
        return ports_output

    nmap_bin = shutil.which("nmap")
    if not nmap_bin:
        print("[!] nmap binary not found in PATH")
        ports_output.touch(exist_ok=True)
        return ports_output

    cmd = [
        nmap_bin,
        "-Pn",
        "-n",
        "--top-ports",
        "1000",
        "--open",
        "-oG",
        "-",
        "-iL",
        str(input_file),
    ]
    cmd.extend(_tool_args(config, "port_scan"))
    print(f"[+] Running: {' '.join(cmd)}")
    open_ports = []
    host_line = re.compile(r"^Host:\s+(?P<host>\S+).*Ports:\s+(?P<ports>.*)$")

    def _port_alert(line: str) -> str | None:
        match = host_line.match(line)
        if not match:
            return None

        host = match.group("host")
        alerts: list[str] = []
        for port_entry in match.group("ports").split(","):
            fields = port_entry.strip().split("/")
            if len(fields) < 2:
                continue
            port, state = fields[0], fields[1]
            if state == "open" and port.isdigit():
                finding = f"{host}:{port}"
                open_ports.append(finding)
                alerts.append(finding)

        if alerts:
            return f"Open ports discovered: {', '.join(alerts[:10])}"
        return None

    result_code = stream_command_with_alerts(
        cmd,
        ports_output,
        title="Port Scan Finding",
        color=0xE74C3C,
        alert_matcher=_port_alert,
    )
    if result_code != 0:
        print(f"[!] nmap exited with code: {result_code}")
        ports_output.touch(exist_ok=True)

    ports_output.write_text("\n".join(open_ports) + ("\n" if open_ports else ""))

    return ports_output


def run_nse_scans(
    input_file,
    config: dict | None = None,
    results_dir: Path | None = None,
    temp_dir: Path | None = None,
):
    print("\n[+] Running NSE Script Scan (nmap --script vuln)...")
    results_root = Path(results_dir) if results_dir is not None else RESULTS_DIR
    temp_root = Path(temp_dir) if temp_dir is not None else TEMP_DIR
    nse_output = results_root / "vulnerabilities" / "nse_results.txt"
    nse_output.parent.mkdir(parents=True, exist_ok=True)

    if not input_file.exists() or input_file.stat().st_size == 0:
        print("[!] No open ports found. Skipping NSE script scan.")
        nse_output.touch(exist_ok=True)
        return nse_output

    nmap_bin = shutil.which("nmap")
    if not nmap_bin:
        print("[!] nmap binary not found in PATH")
        nse_output.touch(exist_ok=True)
        return nse_output

    targets = []
    for line in input_file.read_text().splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        host, _port = line.rsplit(":", 1)
        if host:
            targets.append(host)

    unique_targets = sorted(set(targets))
    if not unique_targets:
        print("[!] No valid hosts parsed for NSE scanning.")
        nse_output.touch(exist_ok=True)
        return nse_output

    target_file = temp_root / "nse_targets.txt"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("\n".join(unique_targets) + "\n")

    cmd = [
        nmap_bin,
        "-Pn",
        "-n",
        "-sV",
        "--script",
        "vuln",
        "-oN",
        "-",
        "-iL",
        str(target_file),
    ]
    cmd.extend(_tool_args(config, "nse_scans"))
    print(f"[+] Running: {' '.join(cmd)}")
    vulnerable_hosts: list[str] = []

    def _nse_alert(line: str) -> str | None:
        if "VULNERABLE" in line.upper():
            vulnerable_hosts.append(line[:300])
            return f"NSE vulnerability: {line[:300]}"
        return None

    result_code = stream_command_with_alerts(
        cmd,
        nse_output,
        title="NSE Finding",
        color=0xE74C3C,
        alert_matcher=_nse_alert,
    )
    if result_code != 0:
        print(f"[!] NSE scan exited with code: {result_code}")
        nse_output.touch(exist_ok=True)

    return nse_output

def run_httpx(
    input_file,
    output_file=None,
    config: dict | None = None,
    results_dir: Path | None = None,
):
    print("\n[+] Probing live web apps (httpx)...")
    results_root = Path(results_dir) if results_dir is not None else RESULTS_DIR
    live_web_output = output_file or results_root / "live_web_apps.txt"
    live_web_output = Path(live_web_output)
    live_web_output.parent.mkdir(parents=True, exist_ok=True)

    httpx_bin = _resolve_httpx_binary()
    if not httpx_bin:
        print("[!] httpx binary not found in PATH (or RECON_HTTPX_BIN override)")
        live_web_output.touch(exist_ok=True)
        return live_web_output

    if not input_file.exists() or input_file.stat().st_size == 0:
        print("[!] No resolved subdomains found. Skipping httpx probing.")
        live_web_output.touch(exist_ok=True)
        return live_web_output
    
    cmd = [httpx_bin, "-l", str(input_file), "-silent", "-o", str(live_web_output)]
    cmd.extend(_tool_args(config, "httpx"))
    print(f"[+] Running: {' '.join(cmd)}")
    try:
        timeout_seconds = int(config.get("execution", {}).get("httpx_timeout", 600)) if isinstance(config, dict) else 600
        result = subprocess.run(cmd, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        print(f"[!] httpx timed out after {timeout_seconds} seconds")
        live_web_output.touch(exist_ok=True)
        return live_web_output

    if result.returncode != 0:
        print(f"[!] httpx exited with code: {result.returncode}")
        live_web_output.touch(exist_ok=True)
        return live_web_output
    
    if live_web_output.exists():
        count = sum(1 for _ in open(live_web_output))
        send_alert("Phase Complete", f"Found {count} live web apps.", 0x3498db)
        
    return live_web_output
