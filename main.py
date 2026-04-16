import argparse
import logging
import shutil
from pathlib import Path

from config import DEFAULT_PIPELINE_CONFIG, TEMP_DIR
from core.config_loader import load_config
from core.orchestrator import Orchestrator, build_context
from core.system_checks import verify_dependencies


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Modular Recon Framework")
    parser.add_argument("-d", "--domain", required=False, default=None, help="Target domain (overrides config)")
    parser.add_argument(
        "-r",
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable/disable recursive bruteforcing (overrides config)",
    )
    parser.add_argument("-w", "--workers", type=int, default=None, help="Number of concurrent workers (overrides config)")
    parser.add_argument("-c", "--config", default=str(DEFAULT_PIPELINE_CONFIG), help="Path to YAML or JSON pipeline config")
    args = parser.parse_args()

    verify_dependencies()
    
    config = load_config(args.config)
    
    target = args.domain or config.get("target", "")
    if not target:
        parser.error("Target domain is required. Provide --domain or set 'target' in config file.")
    
    print(f"\n[+] Starting advanced recon pipeline for: {target}")

    if args.workers is not None:
        config.setdefault("execution", {})["workers"] = args.workers
    if args.recursive is not None:
        config.setdefault("recon", {})["recursive"] = args.recursive
    config["target"] = target

    workspace = Path(__file__).resolve().parent
    ctx = build_context(target, config, workspace)
    orchestrator = Orchestrator(config)
    results = orchestrator.run(ctx)

    print("\n[+] Cleaning temporary files...")
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    
    print(f"\n[=========== RECON COMPLETE ===========]")
    for key in ["resolved_subdomains", "live_web_apps", "raw_urls", "clean_endpoints", "gf_patterns_dir", "screenshots_dir", "fuzzing_dir", "final_report"]:
        artifact = ctx.artifacts.get(key)
        if artifact:
            print(f"[✓] {key.replace('_', ' ').title()}: {artifact.path}")
    print(f"[✓] Tool Results: {len(results)}")

if __name__ == "__main__":
    main()
