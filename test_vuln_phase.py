#!/usr/bin/env python3
"""Test script to run only the vulnerability scanning phase."""

import argparse
import logging
import shutil
from pathlib import Path

from config import DEFAULT_PIPELINE_CONFIG
from core.config_loader import load_config
from core.contracts import Artifact, Phase
from core.orchestrator import Orchestrator, build_context
from core.system_checks import verify_dependencies


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Test Vulnerability Scanner Phase")
    parser.add_argument("-d", "--domain", required=True, help="Target domain")
    parser.add_argument("-c", "--config", default=str(DEFAULT_PIPELINE_CONFIG), help="Path to pipeline config")
    parser.add_argument("--endpoints", required=False, help="Path to clean endpoints file (for testing vuln scanners)")
    parser.add_argument("--live-hosts", required=False, help="Path to live hosts file (for nuclei)")
    parser.add_argument("--resolved", required=False, help="Path to resolved subdomains (for nuclei takeovers)")
    parser.add_argument("--gf-dir", required=False, help="Path to GF patterns directory (for sqlmap/dalfox)")
    args = parser.parse_args()

    verify_dependencies()
    
    config = load_config(args.config)
    config["target"] = args.domain

    workspace = Path(__file__).resolve().parent
    ctx = build_context(args.domain, config, workspace)

    # Populate artifacts from provided paths if they exist
    if args.endpoints and Path(args.endpoints).exists():
        ctx.publish(Artifact(key="clean_endpoints", path=Path(args.endpoints)))
        print(f"[+] Using clean endpoints from: {args.endpoints}")
    
    if args.live_hosts and Path(args.live_hosts).exists():
        ctx.publish(Artifact(key="live_web_apps", path=Path(args.live_hosts)))
        print(f"[+] Using live hosts from: {args.live_hosts}")
    
    if args.resolved and Path(args.resolved).exists():
        ctx.publish(Artifact(key="resolved_subdomains", path=Path(args.resolved)))
        print(f"[+] Using resolved subdomains from: {args.resolved}")
    
    if args.gf_dir and Path(args.gf_dir).exists():
        ctx.publish(Artifact(key="gf_patterns_dir", path=Path(args.gf_dir), kind="directory"))
        print(f"[+] Using GF patterns directory from: {args.gf_dir}")

    # Override pipeline to run only vuln phase
    print(f"\n[+] Running vulnerability phase only for: {args.domain}")
    
    config["pipeline"] = {
        "phases": [
            {
                "name": "vuln",
                "tools": config.get("pipeline", {}).get("phases", [{}])[2].get("tools", []),
                "parallel": True
            }
        ]
    }

    orchestrator = Orchestrator(config)
    results = orchestrator.run(ctx)

    print(f"\n[=========== VULN PHASE COMPLETE ===========]")
    print(f"[✓] Tool Results: {len(results)}")
    
    vuln_dir = ctx.results_dir / "vulnerabilities"
    if vuln_dir.exists():
        print(f"\n[+] Vulnerability results:")
        for result_file in sorted(vuln_dir.glob("*.txt")):
            count = sum(1 for _ in open(result_file)) if result_file.stat().st_size > 0 else 0
            print(f"    - {result_file.name}: {count} lines")
    
    for result in results:
        print(f"[✓] {result.tool}: {result.phase} -> {'SUCCESS' if result.success else 'FAILED'}")
        if result.artifacts:
            for artifact in result.artifacts:
                print(f"    └─ {artifact.key}: {artifact.path}")


if __name__ == "__main__":
    main()
