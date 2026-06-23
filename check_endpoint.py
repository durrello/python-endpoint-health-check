"""Endpoint health checker.

Checks a list of HTTP(S) endpoints and reports whether each is healthy
(reachable and returning an acceptable status). Usable as a CLI or imported
as a module.

Features:
- Per-request timeout and retries with exponential backoff
- Response-time (latency) measurement
- Concurrent checks across endpoints
- Configurable acceptable status codes
- Read endpoints from a file (one URL per line) or the command line
- Human-readable or JSON output; non-zero exit if any endpoint is down
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from typing import Iterable

import requests

DEFAULT_URLS = [
    "https://www.google.com",
    "https://www.youtube.com",
]

DEFAULT_TIMEOUT = 5.0
DEFAULT_RETRIES = 2
DEFAULT_BACKOFF = 0.5
DEFAULT_WORKERS = 8


@dataclass
class CheckResult:
    """The outcome of checking a single endpoint."""
    url: str
    healthy: bool
    status_code: int | None
    latency_ms: float | None
    error: str | None = None


def check_endpoint(
    url: str,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
    ok_statuses: range | Iterable[int] = range(200, 300),
) -> CheckResult:
    """Check a single endpoint, retrying transient failures with backoff.

    Returns a CheckResult with status, latency, and any error captured.
    """
    ok = set(ok_statuses)
    last_error: str | None = None

    for attempt in range(retries + 1):
        start = time.perf_counter()
        try:
            response = requests.get(url, timeout=timeout)
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            healthy = response.status_code in ok
            if healthy or attempt == retries:
                return CheckResult(
                    url=url,
                    healthy=healthy,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                    error=None if healthy else f"unexpected status {response.status_code}",
                )
        except requests.RequestException as exc:
            last_error = type(exc).__name__
            if attempt == retries:
                return CheckResult(url=url, healthy=False, status_code=None,
                                   latency_ms=None, error=last_error)
        # Exponential backoff before the next attempt.
        time.sleep(backoff * (2 ** attempt))

    # Unreachable, but keeps type checkers happy.
    return CheckResult(url=url, healthy=False, status_code=None,
                       latency_ms=None, error=last_error)


def check_all(
    urls: Iterable[str],
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
    workers: int = DEFAULT_WORKERS,
) -> list[CheckResult]:
    """Check every URL concurrently and return a list of CheckResults."""
    urls = list(urls)
    if not urls:
        return []
    with ThreadPoolExecutor(max_workers=min(workers, len(urls))) as pool:
        return list(pool.map(
            lambda u: check_endpoint(u, timeout, retries, backoff), urls
        ))


def load_urls_from_file(path: str) -> list[str]:
    """Read URLs from a file, one per line. Blank lines and # comments ignored."""
    with open(path, encoding="utf-8") as fh:
        return [
            line.strip()
            for line in fh
            if line.strip() and not line.strip().startswith("#")
        ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the health of HTTP endpoints.")
    parser.add_argument("urls", nargs="*", help="URLs to check.")
    parser.add_argument("-f", "--file", help="Read URLs from a file (one per line).")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help="Per-request timeout in seconds.")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES,
                        help="Number of retries on transient failure.")
    parser.add_argument("--backoff", type=float, default=DEFAULT_BACKOFF,
                        help="Base backoff (seconds) between retries.")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help="Max concurrent checks.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args(argv)

    urls = list(args.urls)
    if args.file:
        urls.extend(load_urls_from_file(args.file))
    if not urls:
        urls = DEFAULT_URLS

    results = check_all(urls, args.timeout, args.retries, args.backoff, args.workers)

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        for r in results:
            status = "UP" if r.healthy else "DOWN"
            latency = f"{r.latency_ms}ms" if r.latency_ms is not None else "—"
            detail = "" if r.healthy else f" ({r.error})"
            print(f"[{status}] {r.url}  {latency}{detail}")

    return 0 if all(r.healthy for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
