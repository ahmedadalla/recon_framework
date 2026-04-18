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


def run_url_merge(raw_urls_file, spider_urls_file, config: dict | None = None, results_dir: Path | None = None):
    print("\n[+] Merging wayback and spider URLs...")
    results_root = Path(results_dir) if results_dir is not None else RESULTS_DIR
    clean_urls_output = results_root / "clean_endpoints.txt"
    clean_urls_output.parent.mkdir(parents=True, exist_ok=True)

    inputs = []
    for candidate in (Path(raw_urls_file), Path(spider_urls_file)):
        if candidate.exists() and candidate.stat().st_size > 0:
            inputs.append(candidate)

    if not inputs:
        print("[!] No URLs from wayback or spidering. Skipping merge step.")
        clean_urls_output.touch(exist_ok=True)
        return clean_urls_output

    merged_lines: list[str] = []
    for input_file in inputs:
        merged_lines.extend(
            line.strip()
            for line in input_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            if line.strip()
        )

    if not merged_lines:
        clean_urls_output.touch(exist_ok=True)
        return clean_urls_output

    cmd = ["uro", *_tool_args(config, "url_merge")]
    result = subprocess.run(
        cmd,
        input="\n".join(merged_lines) + "\n",
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"[!] uro exited with code: {result.returncode}. Falling back to unique URL merge.")
        unique_lines = sorted(set(merged_lines))
        clean_urls_output.write_text("\n".join(unique_lines) + ("\n" if unique_lines else ""), encoding="utf-8")
    else:
        clean_urls_output.write_text(result.stdout, encoding="utf-8")

    if clean_urls_output.exists():
        count = sum(1 for _ in open(clean_urls_output))
        send_alert("Phase Complete: URL Merge", f"Extracted **{count}** unique, clean endpoints.", 0xf1c40f)

    return clean_urls_output
