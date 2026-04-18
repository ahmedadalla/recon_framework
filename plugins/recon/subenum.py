from __future__ import annotations

import subprocess

from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool


@register_tool
class SubenumPlugin(ToolPlugin):
    name = "subenum"
    phase = Phase.RECON
    produces = ("subenum_subdomains",)

    def run(self, ctx: RunContext) -> ToolResult:
        output = ctx.temp_dir / f"{ctx.target}_subenum.txt"
        cmd = ["subenum", "-d", ctx.target, "-o", str(output)]
        tool_args = ctx.config.get("tools", {}).get("tool_args", ctx.config.get("tool_args", {}))
        extra = tool_args.get(self.name, []) if isinstance(tool_args, dict) else []
        if isinstance(extra, list):
            cmd.extend(str(item) for item in extra)
        result = subprocess.run(cmd, capture_output=True, text=True)
        artifact = Artifact(key="subenum_subdomains", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=result.returncode == 0, artifacts=[artifact], metrics={"returncode": result.returncode}, message=result.stderr.strip())