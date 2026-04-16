import unittest
import tempfile
from pathlib import Path

from core.registry import TOOL_REGISTRY, load_builtin_plugins, load_external_plugins


class RegistryTests(unittest.TestCase):
    def test_builtin_plugins_register(self):
        load_builtin_plugins()
        for expected in [
            "subfinder",
            "httpx",
            "wayback",
            "spidering",
            "gf_patterns",
            "subenum",
            "oneforall",
            "crtsh",
            "puredns",
            "dnsx_final",
            "nuclei",
            "nuclei_focused",
            "gf_router",
            "port_scan",
            "nse_scans",
            "dalfox",
            "crlfuzz",
            "s3scanner",
            "fuzzing",
            "screenshots",
            "reporting",
        ]:
            self.assertIn(expected, TOOL_REGISTRY)

    def test_external_plugin_loading(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_file = Path(temp_dir) / "custom_plugin.py"
            plugin_file.write_text(
                "from core.contracts import Artifact, Phase, RunContext, ToolPlugin, ToolResult\n"
                "from core.registry import register_tool\n"
                "@register_tool\n"
                "class CustomPlugin(ToolPlugin):\n"
                "    name = 'custom_plugin'\n"
                "    phase = Phase.REPORT\n"
                "    def run(self, ctx: RunContext) -> ToolResult:\n"
                "        return ToolResult(tool=self.name, phase=self.phase, success=True)\n",
                encoding="utf-8",
            )

            load_external_plugins([plugin_file])

            self.assertIn("custom_plugin", TOOL_REGISTRY)


if __name__ == "__main__":
    unittest.main()