# Recon Framework Enhanced

Modular reconnaissance and vulnerability pipeline with plugin-based phases:

- recon
- web
- vuln
- report

## Ubuntu Setup

1. Create and activate a Python virtual environment.
2. Install Python dependencies required by your enabled plugins.
3. Install required CLI tools and make sure they are in your shell PATH.
4. Configure secrets and custom paths with environment variables.

Example environment setup:

```bash
export RECON_WORDLIST="$PWD/wordlists/subdomains-top1million-5000.txt"
export RECON_RESOLVERS="$PWD/wordlists/resolvers.txt"
export DISCORD_WEBHOOK_URL=""
export GEMINI_API_KEY=""
export RECON_HTTPX_BIN=""
```

## Configuration

- Base pipeline config: `config/defaults.json`
- Runtime override: pass `--config` to `main.py`
- CLI overrides:
	- `--domain`
	- `--workers`
	- `--recursive` / `--no-recursive`

## Run

```bash
python main.py --domain example.com --config config/defaults.json
```

## Notes

- Sensitive values are environment-driven; no hardcoded webhook/API key defaults are required.
- Report generation runs from `results/vulnerabilities`.
- Several shell-based pipelines were refactored to safer subprocess/Python I/O flows.