"""Endpoint health checker.

Checks a list of HTTP(S) endpoints and reports whether each is healthy
(reachable and returning a 2xx status). Usable as a CLI or imported as a module.
"""
from __future__ import annotations

import argparse
import sys
from typing import Iterable

import requests

DEFAULT_URLS = [
    "https://www.google.com",
    "https://www.youtube.com",
]

DEFAULT_TIMEOUT = 5.0


def check_endpoint(url: str, timeout: float = DEFAULT_TIMEOUT) -> bool:
    """Return True if the endpoint responds with a 2xx status code."""
    try:
        response = requests.get(url, timeout=timeout)
    except requests.RequestException:
        return False
    return 200 <= response.status_code < 300


def check_all(urls: Iterable[str], timeout: float = DEFAULT_TIMEOUT) -> dict[str, bool]:
    """Check every URL and return a mapping of url -> healthy(bool)."""
    return {url: check_endpoint(url, timeout) for url in urls}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the health of HTTP endpoints.")
    parser.add_argument("urls", nargs="*", default=DEFAULT_URLS,
                        help="URLs to check (defaults to a built-in list).")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help="Per-request timeout in seconds.")
    args = parser.parse_args(argv)

    results = check_all(args.urls or DEFAULT_URLS, args.timeout)
    all_healthy = True
    for url, healthy in results.items():
        status = "UP" if healthy else "DOWN"
        print(f"[{status}] {url}")
        all_healthy = all_healthy and healthy

    # Non-zero exit if any endpoint is down — useful in CI/monitoring.
    return 0 if all_healthy else 1


if __name__ == "__main__":
    sys.exit(main())
