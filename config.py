import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
TEMP_DIR = RESULTS_DIR / "tmp"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG_DIR = BASE_DIR / "config"
DEFAULT_PIPELINE_CONFIG = DEFAULT_CONFIG_DIR / "defaults.json"

WORDLIST = os.getenv("RECON_WORDLIST", "/home/seclinux/mytools/subdomains-top1million-5000.txt")
RESOLVERS = os.getenv("RECON_RESOLVERS", "/home/seclinux/mytools/resolvers.txt")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1491196207379386460/dGcUoXZfXFSHmvoJZXY3EeSeCPcqsbcsIiGyVu6qAmt39rKoG35spFa43ewdZN_2K851")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBmuC9yn9zimt67G5Bo5Ank9tXjV9FxChE")
