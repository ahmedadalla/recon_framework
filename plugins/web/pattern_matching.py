from __future__ import annotations

from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool
from modules.pattern_matching import run_gf_patterns


@register_tool
class PatternMatchingPlugin(ToolPlugin):
    name = "gf_patterns"
    phase = Phase.WEB
    requires = ("clean_endpoints",)
    produces = ("gf_patterns_dir",)

    def run(self, ctx: RunContext) -> ToolResult:
        output = run_gf_patterns(ctx.get_path("clean_endpoints"), ctx.config)
        artifact = Artifact(key="gf_patterns_dir", path=output, kind="directory")
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], message=str(output))