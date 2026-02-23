FROM python:3.11-slim

# Build-time version metadata (injected by CI via --build-arg)
ARG VERSION=dev
ARG COMMIT_SHA=unknown
ARG BUILD_DATE=unknown

# OCI standard image labels
LABEL org.opencontainers.image.title="betterstack-monitor-controller" \
      org.opencontainers.image.description="Kubernetes controller that auto-manages BetterStack uptime monitors from Ingress annotations" \
      org.opencontainers.image.url="https://github.com/luong-komorebi/betterstack-monitor-controller" \
      org.opencontainers.image.source="https://github.com/luong-komorebi/betterstack-monitor-controller" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${COMMIT_SHA}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="MIT"

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies (no dev group, no editable install)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY main.py betterstack_client.py _version.py ./

# Expose version at runtime for logging/health checks
ENV APP_VERSION="${VERSION}" \
    PATH="/app/.venv/bin:$PATH"

CMD ["kopf", "run", "--all-namespaces", "/app/main.py"]
