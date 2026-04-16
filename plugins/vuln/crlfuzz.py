from __future__ import annotations

import re

from config import RESULTS_DIR
from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.discord_alert import stream_command_with_alerts
from core.registry import register_tool


_CRLFUZZ_ALERT = re.compile(r"(?i)(vulnerable|injection|payload|crlf)")


@register_tool
class CRLFuzzPlugin(ToolPlugin):
    name = "crlfuzz"
    phase = Phase.VULN
    requires = ("clean_endpoints",)
    produces = ("crlfuzz_results",)

    def run(self, ctx: RunContext) -> ToolResult:
        vuln_dir = RESULTS_DIR / "vulnerabilities"
        vuln_dir.mkdir(parents=True, exist_ok=True)
        output = vuln_dir / "crlfuzz_results.txt"
        cmd = ["crlfuzz", "-l", str(ctx.get_path("clean_endpoints")), "-o", str(output)]
        tool_args = ctx.config.get("tools", {}).get("tool_args", ctx.config.get("tool_args", {}))
        extra = tool_args.get(self.name, []) if isinstance(tool_args, dict) else []
        if isinstance(extra, list):
            cmd.extend(str(item) for item in extra)

        def _alert_line(line: str) -> str | None:
            if _CRLFUZZ_ALERT.search(line):
                return f"CRLFuzz finding: {line[:300]}"
            return None

        stream_command_with_alerts(
            cmd,
            output,
            title="CRLFuzz Finding",
            color=0xE74C3C,
            alert_matcher=_alert_line,
        )
        artifact = Artifact(key="crlfuzz_results", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact])