FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies (no dev group, no editable install)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY main.py betterstack_client.py ./

ENV PATH="/app/.venv/bin:$PATH"
CMD ["kopf", "run", "--all-namespaces", "/app/main.py"]
