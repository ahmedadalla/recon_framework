import subprocess
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


def run_spidering(live_web_file, config: dict | None = None):
    print("\n[+] Spidering live web applications (katana)...")
    spider_urls_output = TEMP_DIR / "spider_urls.txt"
    spider_urls_output.parent.mkdir(parents=True, exist_ok=True)

    if not live_web_file.exists() or live_web_file.stat().st_size == 0:
        print("[!] No live web targets found. Skipping spidering phase.")
        spider_urls_output.touch(exist_ok=True)
        return spider_urls_output

    cmd = ["katana", "-list", str(live_web_file), "-silent", "-o", str(spider_urls_output)]
    cmd.extend(_tool_args(config, "spidering"))
    subprocess.run(cmd)

    if spider_urls_output.exists():
        count = sum(1 for _ in open(spider_urls_output))
        send_alert("Phase Complete: Spidering", f"Collected **{count}** spidered URLs.", 0xf1c40f)

    return spider_urls_output
