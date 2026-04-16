from __future__ import annotations

import shutil
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from config import RESULTS_DIR
from core.discord_alert import send_alert
from core.discord_alert import stream_command_with_alerts


DEFAULT_NUCLEI_TAGS: dict[str, list[str]] = {
    "xss": ["xss", "cve"],
    "sqli": ["sqli", "cve"],
    "ssrf": ["ssrf", "cve"],
    "redirect": ["redirect", "cve"],
    "lfi": ["lfi", "cve"],
    "rce": ["rce", "cve"],
    "cors": ["cors", "cve"],
    "urls": ["exposure", "misconfig", "cve"],
}


def _run_nuclei(input_file: Path, output_file: Path, tags: list[str] | None = None) -> bool:
    nuclei_bin = shutil.which("nuclei")
    if not nuclei_bin:
        print("[!] nuclei binary not found in PATH. Skipping nuclei routing.")
        output_file.touch(exist_ok=True)
        return False

    cmd = [nuclei_bin, "-l", str(input_file), "-silent", "-o", str(output_file)]
    if tags:
        tag_value = ",".join(tag.strip() for tag in tags if tag.strip())
        if tag_value:
            cmd.extend(["-tags", tag_value])

    subprocess.run(cmd, capture_output=True, text=True)
    return True


def _run_sqlmap(input_file: Path, output_file: Path) -> bool:
    sqlmap_bin = shutil.which("sqlmap")
    if not sqlmap_bin:
        print("[!] sqlmap binary not found in PATH. Falling back to nuclei for SQLi routing.")
        return False

    sqlmap_output_dir = output_file.parent / "sqlmap_output"
    sqlmap_output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sqlmap_bin, "-m", str(input_file), "--batch", f"--output-dir={sqlmap_output_dir}"]
    alert_pattern = re.compile(r"(?i)(appears to be|is vulnerable|sql injection|injectable)")

    def _alert_line(line: str) -> str | None:
        if alert_pattern.search(line):
            return f"SQLMap finding: {line[:300]}"
        return None

    stream_command_with_alerts(
        cmd,
        output_file,
        title="SQLMap Finding",
        color=0xE74C3C,
        alert_matcher=_alert_line,
    )
    return True


def run_gf_routing(gf_dir: Path, config: dict | None = None):
    print("\n[=== PHASE 4B: GF ROUTING ===]")
    routed_dir = RESULTS_DIR / "vulnerabilities" / "gf_routed"
    routed_dir.mkdir(parents=True, exist_ok=True)

    gf_dir = Path(gf_dir)
    if not gf_dir.exists():
        print("[!] GF pattern directory missing. Skipping routed scans.")
        return routed_dir

    pattern_tags = DEFAULT_NUCLEI_TAGS.copy()
    sqlmap_enabled = True
    route_xss = True
    route_sqli = True
    if config:
        routing_config = config.get("pattern_routing", {})
        sqlmap_enabled = bool(routing_config.get("sqlmap_enabled", True))
        custom_tags = routing_config.get("nuclei_tags", {})
        if isinstance(custom_tags, dict):
            for key, value in custom_tags.items():
                if isinstance(value, list):
                    pattern_tags[key] = value

        tools_config = config.get("tools", {})
        enabled_tools = set(tools_config.get("enabled", []) or [])
        run_tools = tools_config.get("run", {}) if isinstance(tools_config.get("run", {}), dict) else {}

        def _tool_active(name: str) -> bool:
            if name in enabled_tools:
                return bool(run_tools.get(name, True))
            return False

        route_xss = not (_tool_active("dalfox") or _tool_active("nuclei") or _tool_active("nuclei_focused"))
        route_sqli = not (_tool_active("sqlmap") or _tool_active("nuclei") or _tool_active("nuclei_focused"))

    routed_patterns: list[str] = []

    xss_file = gf_dir / "xss.txt"
    if route_xss and xss_file.exists() and xss_file.stat().st_size > 0:
        print("[+] Routing XSS matches to nuclei...")
        xss_nuclei_file = routed_dir / "xss_nuclei_results.txt"
        _run_nuclei(xss_file, xss_nuclei_file, pattern_tags.get("xss", ["xss", "cve"]))
        routed_patterns.append("xss/nuclei")
        print("[+] XSS pattern also handled by Dalfox plugin.")

    sqli_file = gf_dir / "sqli.txt"
    if route_sqli and sqli_file.exists() and sqli_file.stat().st_size > 0:
        if sqlmap_enabled:
            print("[+] Routing SQLi matches to sqlmap and nuclei (parallel)...")
        else:
            print("[+] Routing SQLi matches to nuclei only (sqlmap disabled in config)...")

        sqlmap_file = routed_dir / "sqli_sqlmap_results.txt"
        nuclei_file = routed_dir / "sqli_nuclei_results.txt"

        if sqlmap_enabled:
            with ThreadPoolExecutor(max_workers=2) as executor:
                sqlmap_future = executor.submit(_run_sqlmap, sqli_file, sqlmap_file)
                nuclei_future = executor.submit(
                    _run_nuclei,
                    sqli_file,
                    nuclei_file,
                    pattern_tags.get("sqli", ["sqli", "cve"]),
                )
                sqlmap_ok = sqlmap_future.result()
                nuclei_ok = nuclei_future.result()
        else:
            sqlmap_ok = False
            sqlmap_file.touch(exist_ok=True)
            nuclei_ok = _run_nuclei(
                sqli_file,
                nuclei_file,
                pattern_tags.get("sqli", ["sqli", "cve"]),
            )

        if sqlmap_ok:
            routed_patterns.append("sqli/sqlmap")
        if nuclei_ok:
            routed_patterns.append("sqli/nuclei")

    for pattern in ["ssrf", "redirect", "lfi", "rce", "cors", "urls"]:
        pattern_file = gf_dir / f"{pattern}.txt"
        if not pattern_file.exists() or pattern_file.stat().st_size == 0:
            continue

        output_file = routed_dir / f"{pattern}_nuclei_results.txt"
        print(f"[+] Routing {pattern.upper()} matches to nuclei...")
        _run_nuclei(pattern_file, output_file, pattern_tags.get(pattern))
        routed_patterns.append(pattern)

    if routed_patterns:
        send_alert("Phase Complete: GF Routing", f"Routed GF matches for: **{', '.join(routed_patterns)}**", 0x9b59b6)

    return routed_dir