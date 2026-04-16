from __future__ import annotations

from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool
from modules.network import run_port_scan


@register_tool
class PortScanPlugin(ToolPlugin):
    name = "port_scan"
    phase = Phase.VULN
    requires = ("resolved_subdomains",)
    produces = ("open_ports",)

    def run(self, ctx: RunContext) -> ToolResult:
        output = run_port_scan(ctx.get_path("resolved_subdomains"), ctx.config)
        artifact = Artifact(key="open_ports", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], message=str(output))