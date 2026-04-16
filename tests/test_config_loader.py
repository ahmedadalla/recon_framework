import json
import tempfile
import unittest
from pathlib import Path

from core.config_loader import load_config


class ConfigLoaderTests(unittest.TestCase):
    def test_loads_json_override(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "custom.json"
            config_path.write_text(json.dumps({"target": "example.com", "execution": {"workers": 2}}))

            config = load_config(config_path)

            self.assertEqual(config["target"], "example.com")
            self.assertEqual(config["execution"]["workers"], 2)


if __name__ == "__main__":
    unittest.main()