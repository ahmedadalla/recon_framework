from __future__ import annotations

from typing import Any

from config import RESULTS_DIR
from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.discord_alert import stream_command_with_alerts
from core.registry import register_tool


ALERTABLE_SEVERITIES = {"MEDIUM", "HIGH", "CRITICAL"}
SUPPRESSED_NAME_KEYWORDS = {
    "credentials disclosure check",
}


def _nuclei_alert_parser(record: dict[str, Any]) -> str | None:
    info = record.get("info") or {}
    severity = str(info.get("severity") or record.get("severity") or "unknown").upper()
    if severity not in ALERTABLE_SEVERITIES:
        return None

    name = info.get("name") or record.get("template-id") or record.get("template_id") or "Nuclei finding"
    normalized_name = str(name).strip().lower()
    if any(keyword in normalized_name for keyword in SUPPRESSED_NAME_KEYWORDS):
        return None

    if record.get("matcher-status") is False:
        return None

    matched_at = record.get("matched-at") or record.get("matched_at") or record.get("host") or record.get("template-id")
    if matched_at:
        return f"{severity}: {name} @ {matched_at}"
    return f"{severity}: {name}"


@register_tool
class NucleiPlugin(ToolPlugin):
    name = "nuclei"
    phase = Phase.VULN
    requires = ("live_web_apps",)
    produces = ("nuclei_hosts_results",)

    def run(self, ctx: RunContext) -> ToolResult:
        vuln_dir = RESULTS_DIR / "vulnerabilities"
        vuln_dir.mkdir(parents=True, exist_ok=True)
        output = vuln_dir / "nuclei_hosts_results.txt"
        cmd = ["nuclei", "-l", str(ctx.get_path("live_web_apps")), "-jsonl", "-silent"]
        tool_args = ctx.config.get("tools", {}).get("tool_args", ctx.config.get("tool_args", {}))
        extra = tool_args.get(self.name, []) if isinstance(tool_args, dict) else []
        if isinstance(extra, list):
            cmd.extend(str(item) for item in extra)
        stream_command_with_alerts(
            cmd,
            output,
            title="Nuclei Finding",
            color=0xE74C3C,
            jsonl_parser=_nuclei_alert_parser,
        )
        artifact = Artifact(key="nuclei_hosts_results", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact])


@register_tool
class NucleiFocusedPlugin(ToolPlugin):
    name = "nuclei_focused"
    phase = Phase.VULN
    requires = ("clean_endpoints",)
    produces = ("nuclei_focused_results",)

    def run(self, ctx: RunContext) -> ToolResult:
        vuln_dir = RESULTS_DIR / "vulnerabilities"
        vuln_dir.mkdir(parents=True, exist_ok=True)
        output = vuln_dir / "nuclei_focused_results.txt"

        focused_tags = ctx.config.get("nuclei", {}).get(
            "focused_tags",
            ["xss", "sqli", "lfi", "rce", "ssrf", "redirect", "takeover", "exposure", "cve"],
        )
        tags_value = ",".join(str(tag).strip() for tag in focused_tags if str(tag).strip())

        cmd = ["nuclei", "-l", str(ctx.get_path("clean_endpoints")), "-jsonl", "-silent"]
        if tags_value:
            cmd.extend(["-tags", tags_value])
        tool_args = ctx.config.get("tools", {}).get("tool_args", ctx.config.get("tool_args", {}))
        extra = tool_args.get(self.name, []) if isinstance(tool_args, dict) else []
        if isinstance(extra, list):
            cmd.extend(str(item) for item in extra)

        stream_command_with_alerts(
            cmd,
            output,
            title="Nuclei Focused Finding",
            color=0xE67E22,
            jsonl_parser=_nuclei_alert_parser,
        )
        artifact = Artifact(key="nuclei_focused_results", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact])


@register_tool
class NucleiTakeoversPlugin(ToolPlugin):
    name = "nuclei_takeovers"
    phase = Phase.VULN
    requires = ("resolved_subdomains",)
    produces = ("nuclei_takeovers_results",)

    def run(self, ctx: RunContext) -> ToolResult:
        vuln_dir = RESULTS_DIR / "vulnerabilities"
        vuln_dir.mkdir(parents=True, exist_ok=True)
        output = vuln_dir / "nuclei_takeovers_results.txt"

        cmd = [
            "nuclei",
            "-l",
            str(ctx.get_path("resolved_subdomains")),
            "-jsonl",
            "-silent",
            "-tags",
            "takeover",
        ]
        tool_args = ctx.config.get("tools", {}).get("tool_args", ctx.config.get("tool_args", {}))
        extra = tool_args.get(self.name, []) if isinstance(tool_args, dict) else []
        if isinstance(extra, list):
            cmd.extend(str(item) for item in extra)
        stream_command_with_alerts(
            cmd,
            output,
            title="Nuclei Takeover Finding",
            color=0xE74C3C,
            jsonl_parser=_nuclei_alert_parser,
        )
        artifact = Artifact(key="nuclei_takeovers_results", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact])