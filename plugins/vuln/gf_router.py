from __future__ import annotations

from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool
from modules.gf_routing import run_gf_routing


@register_tool
class GfRouterPlugin(ToolPlugin):
    name = "gf_router"
    phase = Phase.VULN
    requires = ("gf_patterns_dir",)
    produces = ("gf_routed_dir",)

    def run(self, ctx: RunContext) -> ToolResult:
        output = run_gf_routing(ctx.get_path("gf_patterns_dir"), ctx.config, results_dir=ctx.results_dir)
        artifact = Artifact(key="gf_routed_dir", path=output, kind="directory")
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], message=str(output))