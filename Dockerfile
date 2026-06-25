# Minimal, non-root image for running the endpoint health checker.
FROM python:3.12-slim

# Don't write .pyc files; flush stdout/stderr immediately (good for logs).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (better layer caching).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY check_endpoint.py .

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser
USER appuser

ENTRYPOINT ["python", "check_endpoint.py"]
# Default args can be overridden at `docker run`:
#   docker run --rm endpoint-check https://example.com --json
CMD ["--help"]
