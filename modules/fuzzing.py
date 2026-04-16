import subprocess
import shutil
from pathlib import Path
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
    
    # ffuf doesn't natively take a list of URLs easily without looping, 
    # but we can use a bash loop to fuzz each live host.
    ffuf_extra = " ".join(_tool_args(config, "fuzzing"))
    cmd = f"""
    while read -r url; do
        host=$(echo "$url" | awk -F/ '{{print $3}}')
        [ -z "$host" ] && continue
        ffuf -u "$url/FUZZ" -w {wordlist} -mc 200,301,403 -ac -s -noninteractive -of json -o {fuzzing_dir}/$host.json {ffuf_extra}
    done < {live_web_file}
    """
    
    result = subprocess.run(cmd, shell=True, executable='/bin/bash')
    if result.returncode != 0:
        print(f"[!] Fuzzing completed with non-zero exit code: {result.returncode}")
    
    send_alert("Phase Complete: Fuzzing", "Directory fuzzing finished.", 0x9b59b6)
    return fuzzing_dir
