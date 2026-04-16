from __future__ import annotations

from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool
from modules.screenshots import run_screenshots


@register_tool
class ScreenshotsPlugin(ToolPlugin):
    name = "screenshots"
    phase = Phase.VULN
    requires = ("live_web_apps",)
    produces = ("screenshots_dir",)

    def run(self, ctx: RunContext) -> ToolResult:
        output = run_screenshots(ctx.get_path("live_web_apps"), ctx.config)
        artifact = Artifact(key="screenshots_dir", path=output, kind="directory")
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], message=str(output))