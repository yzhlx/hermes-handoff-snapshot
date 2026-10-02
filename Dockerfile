# Cloud Hermes Core V1 — container image (stdlib-only, no external Python deps).
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    HERMES_ENV=production \
    HERMES_BIND_HOST=0.0.0.0 \
    HERMES_PORT=8080

WORKDIR /app

# Only the cloud service + static web UI are needed in the container.
COPY cloud_hermes ./cloud_hermes
COPY web ./web

# Runtime config is injected via environment / secret manager (never baked into the image):
#   HERMES_SECRET_KEY, PROVIDER_BASE_URL, PROVIDER_API_KEY, PROVIDER_MODEL,
#   ADMIN_INIT_TOKEN, HERMES_DB_PATH (volume-mounted)
VOLUME ["/data"]
ENV HERMES_DB_PATH=/data/hermes_cloud.db

EXPOSE 8080

# First run boots admin via ADMIN_INIT_TOKEN, then serves forever.
CMD ["python", "-m", "cloud_hermes.main", "--host", "0.0.0.0", "--port", "8080"]
