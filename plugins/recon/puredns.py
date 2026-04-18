from __future__ import annotations

import subprocess

from config import RESOLVERS, WORDLIST
from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool


@register_tool
class PurednsPlugin(ToolPlugin):
    name = "puredns"
    phase = Phase.RECON
    requires = ("subfinder_subdomains", "subenum_subdomains", "oneforall_subdomains", "crtsh_subdomains")
    produces = ("puredns_subdomains",)

    def run(self, ctx: RunContext) -> ToolResult:
        output = ctx.temp_dir / f"{ctx.target}_puredns.txt"
        input_file = ctx.temp_dir / f"{ctx.target}_puredns_input.txt"
        merged: set[str] = set()
        for key in self.requires:
            path = ctx.get_path(key)
            if path.exists():
                merged.update(line.strip() for line in path.read_text().splitlines() if line.strip())
        input_file.write_text("\n".join(sorted(merged)) + ("\n" if merged else ""), encoding="utf-8")
        cmd = ["puredns", "bruteforce", WORDLIST, ctx.target, "-r", RESOLVERS, "-w", str(output), "--quiet"]
        tool_args = ctx.config.get("tools", {}).get("tool_args", ctx.config.get("tool_args", {}))
        extra = tool_args.get(self.name, []) if isinstance(tool_args, dict) else []
        if isinstance(extra, list):
            cmd.extend(str(item) for item in extra)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if not output.exists():
            output.touch(exist_ok=True)
        artifact = Artifact(key="puredns_subdomains", path=output)
        return ToolResult(
            tool=self.name,
            phase=self.phase,
            success=result.returncode == 0,
            artifacts=[artifact],
            metrics={"input_count": len(merged), "returncode": result.returncode},
            message=result.stderr.strip(),
        )