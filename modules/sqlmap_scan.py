import re
import shutil
from pathlib import Path

from core.discord_alert import stream_command_with_alerts


def _tool_args(config: dict | None, tool_name: str) -> list[str]:
    if not isinstance(config, dict):
        return []
    tool_args = config.get("tools", {}).get("tool_args", config.get("tool_args", {}))
    value = tool_args.get(tool_name, []) if isinstance(tool_args, dict) else []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def run_sqlmap(sqli_input, output_file, config: dict | None = None):
    sqlmap_bin = shutil.which("sqlmap")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if not sqli_input.exists() or sqli_input.stat().st_size == 0:
        output_file.touch(exist_ok=True)
        return output_file

    if not sqlmap_bin:
        print("[!] sqlmap binary not found in PATH. Skipping SQLMap scan.")
        output_file.touch(exist_ok=True)
        return output_file

    sqlmap_output_dir = output_file.parent / "sqlmap_output"
    sqlmap_output_dir.mkdir(parents=True, exist_ok=True)
    alert_pattern = re.compile(r"(?i)(appears to be|is vulnerable|sql injection|injectable)")

    urls = [
        line.strip()
        for line in Path(sqli_input).read_text(encoding="utf-8", errors="ignore").splitlines()
        if line.strip()
    ]
    if not urls:
        output_file.touch(exist_ok=True)
        return output_file

    combined_lines: list[str] = []
    sqlmap_args = _tool_args(config, "sqlmap")
    for index, url in enumerate(urls, start=1):
        per_target_output = sqlmap_output_dir / f"{index}.txt"
        cmd = [sqlmap_bin, "-u", url, "--batch", f"--output-dir={sqlmap_output_dir}", *sqlmap_args]

        def _alert_line(line: str, current_url: str = url) -> str | None:
            if alert_pattern.search(line):
                return f"SQLMap finding for {current_url}: {line[:300]}"
            return None

        stream_command_with_alerts(
            cmd,
            per_target_output,
            title="SQLMap Finding",
            color=0xE74C3C,
            alert_matcher=_alert_line,
        )
        if per_target_output.exists():
            combined_lines.append(per_target_output.read_text(encoding="utf-8", errors="ignore"))

    output_file.write_text("".join(combined_lines), encoding="utf-8")
    return output_file
