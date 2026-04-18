import os
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
TEMP_DIR = RESULTS_DIR / "tmp"


def _sanitize_target_name(target: str) -> str:
	name = target.strip().lower()
	return re.sub(r"[^a-z0-9._-]+", "_", name) or "default"


def domain_results_dir(target: str) -> Path:
	return RESULTS_DIR / _sanitize_target_name(target)


def domain_temp_dir(target: str) -> Path:
	return TEMP_DIR / _sanitize_target_name(target)

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG_DIR = BASE_DIR / "config"
DEFAULT_PIPELINE_CONFIG = DEFAULT_CONFIG_DIR / "defaults.json"

WORDLIST = os.getenv("RECON_WORDLIST", str(BASE_DIR / "wordlists" / "subdomains-top1million-5000.txt"))
RESOLVERS = os.getenv("RECON_RESOLVERS", str(BASE_DIR / "wordlists" / "resolvers.txt"))

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
DISCORD_ALERTS_ENABLED = os.getenv("DISCORD_ALERTS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
DISCORD_ALERT_TIMEOUT = float(os.getenv("DISCORD_ALERT_TIMEOUT", "3"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
