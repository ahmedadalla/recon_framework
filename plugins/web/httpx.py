from __future__ import annotations

from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool
from modules.network import run_httpx


@register_tool
class HttpxPlugin(ToolPlugin):
    name = "httpx"
    phase = Phase.WEB
    requires = ("resolved_subdomains",)
    produces = ("live_web_apps",)

    def run(self, ctx: RunContext) -> ToolResult:
        resolved = ctx.get_path("resolved_subdomains")
        output = run_httpx(resolved, config=ctx.config)
        artifact = Artifact(key="live_web_apps", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], message=str(output))