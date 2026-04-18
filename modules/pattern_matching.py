import subprocess
from pathlib import Path
from config import RESULTS_DIR
from core.discord_alert import send_alert


def _tool_args(config: dict | None, tool_name: str) -> list[str]:
    if not isinstance(config, dict):
        return []
    tool_args = config.get("tools", {}).get("tool_args", config.get("tool_args", {}))
    value = tool_args.get(tool_name, []) if isinstance(tool_args, dict) else []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def run_gf_patterns(clean_endpoints, config: dict | None = None, results_dir: Path | None = None):
    print("\n[=== PHASE 4: GF PATTERN MATCHING ===]")
    results_root = Path(results_dir) if results_dir is not None else RESULTS_DIR
    gf_dir = results_root / "gf_patterns"
    gf_dir.mkdir(exist_ok=True)

    if not Path(clean_endpoints).exists() or Path(clean_endpoints).stat().st_size == 0:
        print("[!] No endpoints available for GF pattern matching. Skipping phase.")
        return gf_dir
    
    # Common GF patterns for bug bounty hunting
    desired_patterns = ["xss", "sqli", "ssrf", "redirect", "lfi", "rce", "cors", "urls"]
    if isinstance(config, dict):
        configured_patterns = config.get("gf_patterns", {}).get("desired_patterns", desired_patterns)
        if isinstance(configured_patterns, list) and configured_patterns:
            desired_patterns = [str(item).strip() for item in configured_patterns if str(item).strip()]
    available_patterns = set()
    list_result = subprocess.run(["gf", "-list"], capture_output=True, text=True)
    if list_result.returncode == 0:
        available_patterns = {line.strip() for line in list_result.stdout.splitlines() if line.strip()}

    patterns = [p for p in desired_patterns if p in available_patterns] if available_patterns else desired_patterns
    if not patterns:
        print("[!] No GF patterns available. Skipping phase.")
        return gf_dir

    matched_files = []

    for pattern in patterns:
        output_file = gf_dir / f"{pattern}.txt"

        cmd = ["gf", pattern, *_tool_args(config, "gf_patterns")]
        with Path(clean_endpoints).open("r", encoding="utf-8", errors="ignore") as input_handle, output_file.open("w", encoding="utf-8") as output_handle:
            result = subprocess.run(cmd, stdin=input_handle, stdout=output_handle, stderr=subprocess.DEVNULL, text=True)
        if result.returncode not in (0, 1):
            print(f"[!] gf {pattern} exited with code: {result.returncode}")
        
        # If the file isn't empty, record it
        if output_file.exists() and output_file.stat().st_size > 0:
            matched_files.append(pattern)
            print(f"[✓] Found matches for {pattern}")
        else:
            # Clean up empty files
            output_file.unlink(missing_ok=True)

    if matched_files:
        send_alert("Phase 4 Complete: Pattern Matching", f"GF identified vulnerable parameters for: **{', '.join(matched_files)}**", 0xe67e22)
        
    return gf_dir
