import re
import shutil

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
    cmd = [sqlmap_bin, "-m", str(sqli_input), "--batch", f"--output-dir={sqlmap_output_dir}"]
    cmd.extend(_tool_args(config, "sqlmap"))
    alert_pattern = re.compile(r"(?i)(appears to be|is vulnerable|sql injection|injectable)")

    def _alert_line(line: str) -> str | None:
        if alert_pattern.search(line):
            return f"SQLMap finding: {line[:300]}"
        return None

    stream_command_with_alerts(
        cmd,
        output_file,
        title="SQLMap Finding",
        color=0xE74C3C,
        alert_matcher=_alert_line,
    )
    return output_file
