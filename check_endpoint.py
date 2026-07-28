"""Endpoint health checker.

Checks a list of HTTP(S) endpoints concurrently and reports whether each is
healthy (reachable and returning an expected status). Usable as a CLI or
imported as a module.

Features:
- Concurrent checks (thread pool) for fast multi-endpoint monitoring
- Automatic retries with backoff for transient failures
- Per-endpoint latency measurement
- Plain-text or JSON output (JSON drops into dashboards/alerting)
- Configurable timeout, retries, and accepted status codes
- Non-zero exit code if any endpoint is down (CI / cron friendly)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass

import requests

DEFAULT_URLS = [
    "https://www.google.com",
    "https://www.youtube.com",
]

DEFAULT_TIMEOUT = 5.0
DEFAULT_RETRIES = 2
DEFAULT_BACKOFF = 0.5
DEFAULT_WORKERS = 10


@dataclass
class CheckResult:
    """The outcome of checking a single endpoint."""
    url: str
    healthy: bool
    status_code: int | None
    latency_ms: float | None
    attempts: int
    error: str | None = None


def check_endpoint(
    url: str,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
    accepted_statuses: range | Iterable[int] = range(200, 300),
) -> CheckResult:
    """Check a single endpoint, retrying transient failures.

    Returns a CheckResult with status, latency, and attempt count.
    """
    accepted = set(accepted_statuses)
    last_error: str | None = None
    attempts = 0

    for attempt in range(1, retries + 2):  # initial try + `retries` retries
        attempts = attempt
        start = time.perf_counter()
        try:
            response = requests.get(url, timeout=timeout)
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            if response.status_code in accepted:
                return CheckResult(url, True, response.status_code, latency_ms, attempts)
            last_error = f"unexpected status {response.status_code}"
            # Retry on 5xx; don't retry on 4xx (client errors won't fix themselves).
            if response.status_code < 500:
                return CheckResult(url, False, response.status_code, latency_ms, attempts, last_error)
        except requests.RequestException as exc:
            last_error = type(exc).__name__

        if attempt <= retries:
            time.sleep(backoff * attempt)  # linear backoff

    return CheckResult(url, False, None, None, attempts, last_error)


def check_all(
    urls: Iterable[str],
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    workers: int = DEFAULT_WORKERS,
    accepted_statuses: range | Iterable[int] = range(200, 300),
) -> list[CheckResult]:
    """Check every URL concurrently and return a list of CheckResults."""
    urls = list(urls)
    if not urls:
        return []
    with ThreadPoolExecutor(max_workers=min(workers, len(urls))) as pool:
        return list(
            pool.map(
                lambda u: check_endpoint(u, timeout, retries, accepted_statuses=accepted_statuses),
                urls,
            )
        )


def _print_text(results: list[CheckResult]) -> None:
    for r in results:
        status = "UP" if r.healthy else "DOWN"
        latency = f"{r.latency_ms}ms" if r.latency_ms is not None else "—"
        detail = f" ({r.error})" if r.error and not r.healthy else ""
        print(f"[{status}] {r.url}  {latency}  code={r.status_code or '—'}{detail}")


def load_urls_from_file(path: str) -> list[str]:
    """Read URLs from a file, one per line. Blank lines and `#` comments are ignored."""
    urls: list[str] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the health of HTTP endpoints.")
    parser.add_argument("urls", nargs="*", help="URLs to check (defaults to a built-in list).")
    parser.add_argument("-f", "--file",
                        help="Read URLs from a file (one per line; # comments allowed).")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help="Per-request timeout in seconds.")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES,
                        help="Number of retries on transient failures (5xx / network).")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help="Max concurrent checks.")
    parser.add_argument("--json", action="store_true", help="Output results as JSON.")
    parser.add_argument("--accept", type=str, default="200-299",
                        help="Accepted status codes, e.g. '200-299' or '200,204,301'.")
    args = parser.parse_args(argv)

    accepted = _parse_accept(args.accept)
    urls = list(args.urls)
    if args.file:
        urls.extend(load_urls_from_file(args.file))
    urls = urls or DEFAULT_URLS
    results = check_all(urls, args.timeout, args.retries, args.workers, accepted)

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        _print_text(results)

    return 0 if all(r.healthy for r in results) else 1


def _parse_accept(spec: str) -> set[int]:
    """Parse an accepted-status spec like '200-299' or '200,204,301'."""
    codes: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            codes.update(range(int(lo), int(hi) + 1))
        elif part:
            codes.add(int(part))
    return codes


if __name__ == "__main__":
    sys.exit(main())
