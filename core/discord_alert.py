from config import DISCORD_ALERTS_ENABLED, DISCORD_ALERT_TIMEOUT, DISCORD_WEBHOOK_URL

import json
import os
import subprocess
import threading
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None


_alerts_disabled_for_run = False
_alert_failure_reported = False
_alert_state_lock = threading.Lock()

def send_alert(title, description, color=0x00ff00):
    global _alerts_disabled_for_run
    global _alert_failure_reported

    if _alerts_disabled_for_run:
        return

    if (
        not DISCORD_ALERTS_ENABLED
        or not DISCORD_WEBHOOK_URL
        or DISCORD_WEBHOOK_URL == "YOUR_WEBHOOK_HERE"
        or requests is None
    ):
        return

    data = {"embeds": [{"title": title, "description": description, "color": color}]}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=(1.5, max(1.5, DISCORD_ALERT_TIMEOUT)))
        response.raise_for_status()
    except Exception as e:
        with _alert_state_lock:
            _alerts_disabled_for_run = True
            if not _alert_failure_reported:
                _alert_failure_reported = True
                print(f"[!] Discord alerts disabled for this run after first failure ({type(e).__name__}).")


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
