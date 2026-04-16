from __future__ import annotations

from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool
from modules.reporting import run_reporting


@register_tool
class ReportingPlugin(ToolPlugin):
    name = "reporting"
    phase = Phase.REPORT
    requires = ("vuln_dir",)
    produces = ("final_report",)
    parallel_safe = False

    def run(self, ctx: RunContext) -> ToolResult:
        output = run_reporting(ctx.get_path("vuln_dir"), ctx.target)
        artifact = Artifact(key="final_report", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], message=str(output))