import shutil
import subprocess
from pathlib import Path

from config import TEMP_DIR
from core.discord_alert import send_alert


def _tool_args(config: dict | None, tool_name: str) -> list[str]:
    if not isinstance(config, dict):
        return []
    tool_args = config.get("tools", {}).get("tool_args", config.get("tool_args", {}))
    value = tool_args.get(tool_name, []) if isinstance(tool_args, dict) else []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def run_wayback_gathering(live_web_file, config: dict | None = None, temp_dir: Path | None = None):
    print("\n[+] Gathering archived URLs (waybackurls)...")
    temp_root = Path(temp_dir) if temp_dir is not None else TEMP_DIR
    raw_urls_output = temp_root / "raw_urls.txt"
    raw_urls_output.parent.mkdir(parents=True, exist_ok=True)

    if not live_web_file.exists() or live_web_file.stat().st_size == 0:
        print("[!] No live web targets found. Skipping wayback gathering.")
        raw_urls_output.touch(exist_ok=True)
        return raw_urls_output

    wayback_bin = shutil.which("waybackurls")
    gau_bin = shutil.which("gau")

    if wayback_bin:
        cmd = [wayback_bin]
    elif gau_bin:
        cmd = [gau_bin]
    else:
        print("[!] Neither waybackurls nor gau was found in PATH. Skipping.")
        raw_urls_output.touch(exist_ok=True)
        return raw_urls_output

    cmd.extend(_tool_args(config, "wayback"))

    with open(live_web_file, "r") as input_handle, open(raw_urls_output, "w") as output_handle:
        result = subprocess.run(cmd, stdin=input_handle, stdout=output_handle, stderr=subprocess.DEVNULL, text=True)
    if result.returncode != 0:
        print(f"[!] {' '.join(cmd[:1])} exited with code: {result.returncode}")
        raw_urls_output.touch(exist_ok=True)
        return raw_urls_output

    if raw_urls_output.exists():
        count = sum(1 for _ in open(raw_urls_output))
        send_alert("Phase Complete: Wayback Gathering", f"Collected **{count}** archived URLs.", 0x95a5a6)

    return raw_urls_output