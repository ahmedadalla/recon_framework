from __future__ import annotations

import json
import subprocess

from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool


@register_tool
class OneForAllPlugin(ToolPlugin):
    name = "oneforall"
    phase = Phase.RECON
    produces = ("oneforall_subdomains",)

    def run(self, ctx: RunContext) -> ToolResult:
        cmd = ["oneforall", "--target", ctx.target, "--path", str(ctx.temp_dir), "--fmt", "json", "run"]
        tool_args = ctx.config.get("tools", {}).get("tool_args", ctx.config.get("tool_args", {}))
        extra = tool_args.get(self.name, []) if isinstance(tool_args, dict) else []
        if isinstance(extra, list):
            cmd.extend(str(item) for item in extra)
        result = subprocess.run(cmd, capture_output=True, text=True)
        json_file = ctx.temp_dir / f"{ctx.target}.json"
        output = ctx.temp_dir / f"{ctx.target}_oneforall.txt"
        subdomains: set[str] = set()
        parse_error = ""
        if json_file.exists():
            try:
                with json_file.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                for entry in data:
                    value = entry.get("subdomain")
                    if value:
                        subdomains.add(value)
            except Exception as exc:
                parse_error = str(exc)
        output.write_text("\n".join(sorted(subdomains)) + ("\n" if subdomains else ""), encoding="utf-8")
        artifact = Artifact(key="oneforall_subdomains", path=output)
        message = result.stderr.strip()
        if parse_error:
            message = f"{message}; parse_error={parse_error}" if message else f"parse_error={parse_error}"
        return ToolResult(
            tool=self.name,
            phase=self.phase,
            success=result.returncode == 0,
            artifacts=[artifact],
            metrics={"count": len(subdomains), "returncode": result.returncode},
            message=message,
        )