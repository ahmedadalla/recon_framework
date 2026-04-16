from __future__ import annotations

from config import RESULTS_DIR
from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool
from modules.sqlmap_scan import run_sqlmap


@register_tool
class SqlmapPlugin(ToolPlugin):
    name = "sqlmap"
    phase = Phase.VULN
    requires = ("gf_patterns_dir",)
    produces = ("sqlmap_results",)

    def run(self, ctx: RunContext) -> ToolResult:
        sqli_file = ctx.get_path("gf_patterns_dir") / "sqli.txt"
        vuln_dir = RESULTS_DIR / "vulnerabilities"
        vuln_dir.mkdir(parents=True, exist_ok=True)
        output = vuln_dir / "sqlmap_results.txt"
        output = run_sqlmap(sqli_file, output, ctx.config)
        artifact = Artifact(key="sqlmap_results", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], message=str(output))
