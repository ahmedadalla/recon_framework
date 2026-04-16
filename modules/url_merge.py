import subprocess
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


def run_url_merge(raw_urls_file, spider_urls_file, config: dict | None = None):
    print("\n[+] Merging wayback and spider URLs...")
    clean_urls_output = RESULTS_DIR / "clean_endpoints.txt"
    clean_urls_output.parent.mkdir(parents=True, exist_ok=True)

    inputs = []
    for candidate in (Path(raw_urls_file), Path(spider_urls_file)):
        if candidate.exists() and candidate.stat().st_size > 0:
            inputs.append(candidate)

    if not inputs:
        print("[!] No URLs from wayback or spidering. Skipping merge step.")
        clean_urls_output.touch(exist_ok=True)
        return clean_urls_output

    merged = " ".join(str(path) for path in inputs)
    uro_args = " ".join(_tool_args(config, "url_merge"))
    subprocess.run(f"cat {merged} | uro {uro_args} > {clean_urls_output}", shell=True)

    if clean_urls_output.exists():
        count = sum(1 for _ in open(clean_urls_output))
        send_alert("Phase Complete: URL Merge", f"Extracted **{count}** unique, clean endpoints.", 0xf1c40f)

    return clean_urls_output
