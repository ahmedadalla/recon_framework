from __future__ import annotations

import json

from config import RESULTS_DIR
from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.discord_alert import stream_command_with_alerts
from core.registry import register_tool


@register_tool
class DalfoxPlugin(ToolPlugin):
    name = "dalfox"
    phase = Phase.VULN
    requires = ("gf_patterns_dir",)
    produces = ("dalfox_results",)

    def run(self, ctx: RunContext) -> ToolResult:
        xss_file = ctx.get_path("gf_patterns_dir") / "xss.txt"
        vuln_dir = RESULTS_DIR / "vulnerabilities"
        vuln_dir.mkdir(parents=True, exist_ok=True)
        output = vuln_dir / "dalfox_results.txt"
        if xss_file.exists() and xss_file.stat().st_size > 0:
            cmd = ["dalfox", "file", str(xss_file), "-o", str(output)]
            tool_args = ctx.config.get("tools", {}).get("tool_args", ctx.config.get("tool_args", {}))
            extra = tool_args.get(self.name, []) if isinstance(tool_args, dict) else []
            if isinstance(extra, list):
                cmd.extend(str(item) for item in extra)

            def _dalfox_jsonl_parser(record: dict) -> str | None:
                if str(record.get("type") or "").upper() != "V":
                    return None

                # Send complete finding context so alerts include URL, payload, CWE, severity, and evidence.
                pretty = json.dumps(record, ensure_ascii=False, indent=2)
                return f"Dalfox verified finding:\n```json\n{pretty}\n```"

            stream_command_with_alerts(
                cmd,
                output,
                title="Dalfox Finding",
                color=0xE74C3C,
                jsonl_parser=_dalfox_jsonl_parser,
            )
        else:
            output.touch(exist_ok=True)
        artifact = Artifact(key="dalfox_results", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact])