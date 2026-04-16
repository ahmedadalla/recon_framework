from config import DISCORD_WEBHOOK_URL

import os
import subprocess
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

def send_alert(title, description, color=0x00ff00):
    if not DISCORD_WEBHOOK_URL or DISCORD_WEBHOOK_URL == "YOUR_WEBHOOK_HERE" or requests is None:
        return
    
    data = {"embeds": [{"title": title, "description": description, "color": color}]}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)
    except Exception as e:
        print(f"[!] Failed to send Discord alert: {e}")


def stream_command_with_alerts(
    cmd,
    output_file: Path,
    *,
    title: str,
    color: int = 0xE74C3C,
    alert_matcher=None,
    jsonl_parser=None,
):
    output_file.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )

    seen_alerts: set[str] = set()
    with output_file.open("w", encoding="utf-8") as handle:
        if process.stdout is None:
            return 1

        for line in iter(process.stdout.readline, ""):
            handle.write(line)
            handle.flush()

            stripped = line.strip()
            if not stripped:
                continue

            alert_text = None
            if jsonl_parser is not None and stripped.startswith("{"):
                try:
                    alert_text = jsonl_parser(json.loads(stripped))
                except Exception:
                    alert_text = None
            elif alert_matcher is not None:
                match = alert_matcher(stripped)
                if match:
                    alert_text = match

            if alert_text and alert_text not in seen_alerts:
                seen_alerts.add(alert_text)
                send_alert(title, alert_text, color)

    return process.wait()
