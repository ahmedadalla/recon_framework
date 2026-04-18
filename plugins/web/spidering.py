from __future__ import annotations

from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool
from modules.spidering import run_spidering


@register_tool
class SpideringPlugin(ToolPlugin):
    name = "spidering"
    phase = Phase.WEB
    requires = ("live_web_apps",)
    produces = ("spider_urls",)

    def run(self, ctx: RunContext) -> ToolResult:
        output = run_spidering(ctx.get_path("live_web_apps"), ctx.config, temp_dir=ctx.temp_dir)
        artifact = Artifact(key="spider_urls", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], message=str(output))