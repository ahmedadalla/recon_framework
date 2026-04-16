from __future__ import annotations

from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool
from modules.network import run_nse_scans


@register_tool
class NseScansPlugin(ToolPlugin):
    name = "nse_scans"
    phase = Phase.VULN
    requires = ("open_ports",)
    produces = ("nse_results",)

    def run(self, ctx: RunContext) -> ToolResult:
        output = run_nse_scans(ctx.get_path("open_ports"), ctx.config)
        artifact = Artifact(key="nse_results", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], message=str(output))