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


def run_screenshots(live_web_file, config: dict | None = None):
    print("\n[+] Gathering Screenshots (gowitness)...")
    screenshots_dir = RESULTS_DIR / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    if not Path(live_web_file).exists() or Path(live_web_file).stat().st_size == 0:
        print("[!] No live web targets found. Skipping screenshots.")
        return screenshots_dir

    gowitness_bin = shutil.which("gowitness")
    if not gowitness_bin:
        print("[!] gowitness binary not found in PATH. Skipping screenshots.")
        return screenshots_dir

    def _count_screenshots():
        return sum(1 for _ in screenshots_dir.rglob("*.jpeg")) + sum(1 for _ in screenshots_dir.rglob("*.png"))

    before_count = _count_screenshots()
    
    # Gowitness v3 command (chromedp, fastest when Chrome is present)
    cmd_v3 = [
        gowitness_bin,
        "scan",
        "file",
        "-f",
        str(live_web_file),
        "-s",
        str(screenshots_dir),
        "--write-none",
        "-T",
        "120",
        "-q",
    ]
    cmd_v3.extend(_tool_args(config, "screenshots"))
    result = subprocess.run(cmd_v3, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if result.returncode != 0:
        # Gowitness v3 fallback: gorod driver works without local Chrome installation.
        cmd_v3_gorod = [
            gowitness_bin,
            "scan",
            "file",
            "-f",
            str(live_web_file),
            "-s",
            str(screenshots_dir),
            "--driver",
            "gorod",
            "--write-none",
            "-T",
            "120",
            "--delay",
            "5",
            "-q",
        ]
        result = subprocess.run(cmd_v3_gorod, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Last-resort retry for v3: process URLs one by one with gorod when batch mode yields no files.
    if _count_screenshots() == before_count:
        try:
            with open(live_web_file, "r") as handle:
                targets = [line.strip() for line in handle if line.strip()]
        except Exception:
            targets = []

        for url in targets:
            subprocess.run([
                gowitness_bin,
                "scan",
                "single",
                "-u",
                url,
                "-s",
                str(screenshots_dir),
                "--driver",
                "gorod",
                "--write-none",
                "-T",
                "120",
                "--delay",
                "5",
                "-q",
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if _count_screenshots() == before_count:
        # Fallback for older gowitness versions
        cmd_legacy = [
            gowitness_bin,
            "file",
            "-f",
            str(live_web_file),
            "--destination",
            str(screenshots_dir),
            "--disable-logging",
        ]
        subprocess.run(cmd_legacy, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    added = _count_screenshots() - before_count
    if added <= 0:
        print("[!] Screenshot run completed but no new image files were created.")
    else:
        print(f"[✓] Captured {added} new screenshots.")
    
    send_alert("Phase Complete: Screenshots", f"Screenshots saved to {screenshots_dir}", 0x34495e)
    return screenshots_dir
