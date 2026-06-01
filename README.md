# python-endpoint-health-check

A small, tested Python tool that checks whether HTTP(S) endpoints are healthy (reachable and
returning a 2xx status). Use it from the command line or import it as a module. It exits non-zero if
any endpoint is down, so it drops straight into CI or a cron-based monitor.

## Usage

```bash
pip install -r requirements.txt

# Check the built-in default list
python check_endpoint.py

# Check specific URLs with a custom timeout
python check_endpoint.py https://example.com https://api.myservice.com --timeout 3
```

Example output:

```
[UP] https://example.com
[DOWN] https://api.myservice.com
```

Exit code is `0` only if every endpoint is healthy — useful for alerting.

## As a module

```python
from check_endpoint import check_endpoint, check_all

check_endpoint("https://example.com")        # -> True/False
check_all(["https://a.com", "https://b.com"]) # -> {url: bool}
```

## Development

```bash
pip install pytest ruff
ruff check .
pytest -q
```

CI (`.github/workflows/python-ci.yml`) runs ruff + pytest on every push and PR.

## What this demonstrates

- Clean, testable Python (functions, type hints, proper exception handling, a real timeout)
- A CLI with `argparse` and meaningful exit codes
- Unit tests with mocked HTTP calls
- Lint + test automation in GitHub Actions

## License

MIT
