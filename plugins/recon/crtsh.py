from __future__ import annotations

import subprocess

from config import TEMP_DIR
from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult
from core.registry import register_tool


@register_tool
class CrtshPlugin(ToolPlugin):
    name = "crtsh"
    phase = Phase.RECON
    produces = ("crtsh_subdomains",)

    def run(self, ctx: RunContext) -> ToolResult:
        output = TEMP_DIR / "cert_sh.txt"
        try:
            import requests
            response = requests.get(f"https://crt.sh/?q=%25.{ctx.target}&output=json", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception:
            data = []

        subdomains: set[str] = set()
        for entry in data:
            for sub in entry.get("name_value", "").split("\n"):
                sub = sub.strip().lower()
                if not sub.startswith("*.") and sub.endswith("." + ctx.target):
                    subdomains.add(sub)

        output.write_text("\n".join(sorted(subdomains)) + ("\n" if subdomains else ""), encoding="utf-8")
        artifact = Artifact(key="crtsh_subdomains", path=output)
        return ToolResult(tool=self.name, phase=self.phase, success=True, artifacts=[artifact], metrics={"count": len(subdomains)})