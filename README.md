# python-endpoint-health-check

A small, tested Python tool that checks whether HTTP(S) endpoints are healthy. Use it from the
command line or import it as a module. It measures latency, retries transient failures with
exponential backoff, checks endpoints concurrently, and exits non-zero if any endpoint is down —
so it drops straight into CI or a cron-based monitor.

## Features

- **Retries with exponential backoff** — transient blips don't cause false alarms
- **Latency measurement** — response time in milliseconds for every endpoint
- **Concurrent checks** — endpoints are checked in parallel (thread pool)
- **Configurable acceptable statuses** — treat e.g. `403` as healthy if you need to
- **Flexible input** — pass URLs as args, from a file (`--file`), or use the built-in defaults
- **Human or JSON output** — `--json` for machine-readable results
- **Meaningful exit codes** — `0` only if every endpoint is healthy

## Usage

```bash
pip install -r requirements.txt

# Check the built-in default list
python check_endpoint.py

# Check specific URLs with a custom timeout
python check_endpoint.py https://example.com https://api.myservice.com --timeout 3

# Check URLs listed in a file (one per line, # comments allowed)
python check_endpoint.py --file endpoints.txt

# Tune retries / backoff / concurrency
python check_endpoint.py --file endpoints.txt --retries 3 --backoff 0.5 --workers 16

# Machine-readable output for dashboards / alerting
python check_endpoint.py --file endpoints.txt --json
```

Example output:

```
[UP] https://example.com  142.3ms
[DOWN] https://api.myservice.com  — (ConnectTimeout)
```

JSON output:

```json
[
  {
    "url": "https://example.com",
    "healthy": true,
    "status_code": 200,
    "latency_ms": 142.3,
    "error": null
  }
]
```

Exit code is `0` only if every endpoint is healthy — useful for alerting and CI gates.

## As a module

```python
from check_endpoint import check_endpoint, check_all

result = check_endpoint("https://example.com")   # -> CheckResult(...)
result.healthy        # True/False
result.latency_ms     # response time
result.status_code    # HTTP status

results = check_all(["https://a.com", "https://b.com"])  # concurrent -> [CheckResult, ...]
```

## Development

```bash
pip install pytest ruff
ruff check .
pytest -q
```

CI (`.github/workflows/python-ci.yml`) runs ruff + pytest on every push and PR.

## What this demonstrates

- Clean, testable Python: dataclasses, type hints, exception handling, real timeouts
- Resilience patterns: retries with exponential backoff
- Concurrency with `ThreadPoolExecutor`
- A proper CLI (`argparse`) with file input, JSON output, and meaningful exit codes
- Unit tests with mocked HTTP calls (including retry and concurrency paths)
- Lint + test automation in GitHub Actions

## License

MIT
