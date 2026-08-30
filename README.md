# python-endpoint-health-check

A small, tested Python tool that checks whether HTTP(S) endpoints are healthy — reachable and
returning an expected status. It checks endpoints **concurrently**, **retries** transient failures,
measures **latency**, and can emit **JSON** for dashboards/alerting. It exits non-zero if any
endpoint is down, so it drops straight into CI or a cron-based monitor.

## Features

- **Concurrent checks** — a thread pool checks many endpoints in parallel
- **Automatic retries** — transient failures (5xx, network errors) are retried with backoff; 4xx
  client errors are not retried (they won't fix themselves)
- **Latency measurement** — per-endpoint response time in milliseconds
- **Flexible status matching** — accept a range (`200-299`) or a list (`200,204,301`)
- **Text or JSON output** — JSON for piping into monitoring/alerting
- **CI/cron friendly** — non-zero exit code if any endpoint is down

## Usage

```bash
pip install -r requirements.txt

# Check the built-in default list
python check_endpoint.py

# Check specific URLs with a custom timeout + retries
python check_endpoint.py https://example.com https://api.myservice.com --timeout 3 --retries 3

# Accept redirects as healthy
python check_endpoint.py https://example.com --accept 200-399

# JSON output (for dashboards / alerting)
python check_endpoint.py https://example.com --json
```

Example text output:

```
[UP]   https://example.com       142.3ms  code=200
[DOWN] https://api.myservice.com  —        code=—  (ConnectionError)
```

Example JSON output:

```json
[
  {
    "url": "https://example.com",
    "healthy": true,
    "status_code": 200,
    "latency_ms": 142.3,
    "attempts": 1,
    "error": null
  }
]
```

Exit code is `0` only if every endpoint is healthy — useful for alerting.

## Run with Docker

```bash
docker build -t endpoint-check .
docker run --rm endpoint-check https://example.com https://google.com --json
```

## As a module

```python
from check_endpoint import check_endpoint, check_all

result = check_endpoint("https://example.com")   # -> CheckResult(...)
print(result.healthy, result.latency_ms)

results = check_all(["https://a.com", "https://b.com"])  # -> list[CheckResult]
```

## Development

```bash
pip install pytest ruff
ruff check .
pytest -q
```

CI (`.github/workflows/python-ci.yml`) runs ruff + pytest on every push and PR.

## What this demonstrates

- Clean, testable Python (dataclasses, type hints, proper exception handling, real timeouts)
- Concurrency with `ThreadPoolExecutor` and a sensible retry/backoff strategy
- A CLI with `argparse`, JSON output, and meaningful exit codes
- Thorough unit tests with mocked HTTP calls (retries, status handling, concurrency)
- Lint + test automation in GitHub Actions
- A minimal, non-root Docker image

## License

MIT


---

<div align="center">

### Built by

**Durrell Gemuh** - Founder @ NextGen Playground | DevOps & Cloud Infrastructure Engineer | AWS Community Builder

[![Portfolio](https://img.shields.io/badge/Portfolio-durrellgemuh.com-000?style=flat-square&logo=vercel)](https://durrellgemuh.com)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-durrello-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/durrello/)
[![Dev.to](https://img.shields.io/badge/Dev.to-durrello-0A0A0A?style=flat-square&logo=devdotto)](https://dev.to/durrello)
[![X](https://img.shields.io/badge/X-@durrelloo-000?style=flat-square&logo=x)](https://x.com/durrelloo)
[![GitHub](https://img.shields.io/badge/GitHub-durrello-181717?style=flat-square&logo=github)](https://github.com/durrello)
[![Email](https://img.shields.io/badge/Email-durrell.gemuh.a@gmail.com-EA4335?style=flat-square&logo=gmail)](mailto:durrell.gemuh.a@gmail.com)

---

⭐ **Star this repo** if you found it useful - it helps others discover it!

</div>
