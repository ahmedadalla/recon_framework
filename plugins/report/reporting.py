from __future__ import annotations

from config import RESULTS_DIR
from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool
from modules.reporting import run_reporting


@register_tool
class ReportingPlugin(ToolPlugin):
    name = "reporting"
    phase = Phase.REPORT
    produces = ("final_report",)
    parallel_safe = False

    def run(self, ctx: RunContext) -> ToolResult:
        vuln_dir = RESULTS_DIR / "vulnerabilities"
        output = run_reporting(vuln_dir, ctx.target)
        artifact = Artifact(key="final_report", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], message=str(output))