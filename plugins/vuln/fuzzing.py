from __future__ import annotations

from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool
from modules.fuzzing import run_fuzzing


@register_tool
class FuzzingPlugin(ToolPlugin):
    name = "fuzzing"
    phase = Phase.VULN
    requires = ("live_web_apps",)
    produces = ("fuzzing_dir",)

    def run(self, ctx: RunContext) -> ToolResult:
        output = run_fuzzing(ctx.get_path("live_web_apps"), ctx.config, results_dir=ctx.results_dir)
        artifact = Artifact(key="fuzzing_dir", path=output, kind="directory")
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], message=str(output))