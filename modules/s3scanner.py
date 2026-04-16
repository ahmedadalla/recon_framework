from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse


_S3_BUCKET_NAME = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")


def _normalize_candidate(value: str) -> str | None:
    candidate = value.strip().rstrip(".")
    if not candidate:
        return None
    if not _S3_BUCKET_NAME.fullmatch(candidate):
        return None
    return candidate


def _extract_from_host(hostname: str, path: str) -> str | None:
    host = hostname.lower()

    if host == "s3.amazonaws.com" or host.startswith("s3.") or host.startswith("s3-"):
        segments = [segment for segment in path.split("/") if segment]
        if segments:
            return _normalize_candidate(segments[0])
        return None

    match = re.match(r"^(?P<bucket>[a-z0-9.-]+)\.s3(?:[.-][a-z0-9-]+)?(?:\.dualstack)?\.amazonaws\.com(?:\.cn)?$", host)
    if match:
        return _normalize_candidate(match.group("bucket"))

    match = re.match(r"^(?P<bucket>[a-z0-9.-]+)\.s3-website(?:[.-][a-z0-9-]+)?\.amazonaws\.com(?:\.cn)?$", host)
    if match:
        return _normalize_candidate(match.group("bucket"))

    return None


def build_bucket_file(endpoints_file: Path, bucket_file: Path) -> Path:
    bucket_file.parent.mkdir(parents=True, exist_ok=True)

    if not endpoints_file.exists() or endpoints_file.stat().st_size == 0:
        bucket_file.write_text("", encoding="utf-8")
        return bucket_file

    buckets: list[str] = []
    seen: set[str] = set()

    with endpoints_file.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue

            parsed = urlparse(line if "://" in line else f"//{line}", scheme="https")
            hostname = parsed.hostname
            if not hostname:
                continue

            candidate = _extract_from_host(hostname, parsed.path or "")
            if not candidate and hostname.lower().endswith("amazonaws.com"):
                segments = [segment for segment in (parsed.path or "").split("/") if segment]
                if segments:
                    candidate = _normalize_candidate(segments[0])

            if not candidate or candidate in seen:
                continue

            seen.add(candidate)
            buckets.append(candidate)

    bucket_file.write_text("\n".join(buckets) + ("\n" if buckets else ""), encoding="utf-8")
    return bucket_file