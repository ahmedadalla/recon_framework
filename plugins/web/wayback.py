from __future__ import annotations

from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool
from modules.wayback import run_wayback_gathering


@register_tool
class WaybackPlugin(ToolPlugin):
    name = "wayback"
    phase = Phase.WEB
    requires = ("live_web_apps",)
    produces = ("raw_urls",)

    def run(self, ctx: RunContext) -> ToolResult:
        output = run_wayback_gathering(ctx.get_path("live_web_apps"), ctx.config)
        artifact = Artifact(key="raw_urls", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], message=str(output))