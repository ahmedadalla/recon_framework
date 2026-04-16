from __future__ import annotations

import subprocess

from config import RESULTS_DIR, TEMP_DIR
from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool


@register_tool
class DnsxFinalPlugin(ToolPlugin):
    name = "dnsx_final"
    phase = Phase.RECON
    requires = ("subfinder_subdomains", "subenum_subdomains", "oneforall_subdomains", "crtsh_subdomains", "puredns_subdomains")
    produces = ("resolved_subdomains",)

    def run(self, ctx: RunContext) -> ToolResult:
        master = RESULTS_DIR / "master_subdomains.txt"
        merged: set[str] = set()
        for key in self.requires:
            path = ctx.get_path(key)
            if path.exists():
                merged.update(line.strip() for line in path.read_text().splitlines() if line.strip())
        master.write_text("\n".join(sorted(merged)) + ("\n" if merged else ""), encoding="utf-8")
        output = RESULTS_DIR / "final_resolved_subdomains.txt"
        cmd = ["dnsx", "-l", str(master), "-silent", "-o", str(output)]
        tool_args = ctx.config.get("tools", {}).get("tool_args", ctx.config.get("tool_args", {}))
        extra = tool_args.get(self.name, []) if isinstance(tool_args, dict) else []
        if isinstance(extra, list):
            cmd.extend(str(item) for item in extra)
        subprocess.run(cmd, capture_output=True, text=True)
        artifact = Artifact(key="resolved_subdomains", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], metrics={"input_count": len(merged)})