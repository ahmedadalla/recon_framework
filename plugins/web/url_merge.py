from __future__ import annotations

from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool
from modules.url_merge import run_url_merge


@register_tool
class UrlMergePlugin(ToolPlugin):
    name = "url_merge"
    phase = Phase.WEB
    requires = ("raw_urls", "spider_urls")
    produces = ("clean_endpoints",)
    parallel_safe = False

    def run(self, ctx: RunContext) -> ToolResult:
        output = run_url_merge(ctx.get_path("raw_urls"), ctx.get_path("spider_urls"), ctx.config)
        artifact = Artifact(key="clean_endpoints", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], message=str(output))
