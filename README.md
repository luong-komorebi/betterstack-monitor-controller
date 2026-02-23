# betterstack-monitor-controller

[![CI](https://github.com/luong-komorebi/betterstack-monitor-controller/actions/workflows/ci.yml/badge.svg)](https://github.com/luong-komorebi/betterstack-monitor-controller/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A lightweight Kubernetes controller that automatically manages [BetterStack Uptime](https://betterstack.com/uptime) monitors by watching `Ingress` resources. Annotate an Ingress and the controller will create, update, or delete the corresponding monitors — no manual configuration required.

## How it works

The controller uses [kopf](https://kopf.readthedocs.io/) to watch `networking.k8s.io/v1` Ingress events. When an Ingress carries the `betterstack.io/monitor: "true"` annotation the controller reconciles BetterStack monitors for every hostname defined in `spec.rules`.

| Event | Action |
| ----- | ------ |
| Ingress created | Creates one monitor per host |
| Ingress updated | Updates existing monitors; removes monitors for deleted hosts |
| Ingress deleted | Deletes all monitors associated with the Ingress |

Monitor IDs are persisted back to the Ingress as `betterstack.io/monitor-ids` (a JSON map of `host → monitor_id`) so reconciliation is idempotent across controller restarts.

## Annotations

| Annotation | Required | Default | Description |
| ---------- | -------- | ------- | ----------- |
| `betterstack.io/monitor` | Yes | — | Set to `"true"` to enable monitoring |
| `betterstack.io/path` | No | `/api/health` | HTTP path checked by the monitor |
| `betterstack.io/monitor-ids` | Auto-managed | `{}` | JSON map of host → monitor ID written back by the controller |

### Example Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app
  annotations:
    betterstack.io/monitor: "true"
    betterstack.io/path: "/healthz"
spec:
  rules:
    - host: my-app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-app
                port:
                  number: 80
```

## Deployment

### Prerequisites

- Kubernetes ≥ 1.24
- A [BetterStack API token](https://betterstack.com/docs/uptime/api/getting-started-with-the-uptime-api/) with monitor read/write permissions

### kubectl

```bash
# Create the secret
kubectl create namespace monitoring
kubectl create secret generic betterstack-monitor \
  --namespace monitoring \
  --from-literal=api-token=<YOUR_TOKEN>

# Deploy
kubectl apply -f k8s/deploy.yaml
```

## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies including dev tools
uv sync --group dev

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov --cov-report=term-missing
```

## CI

GitHub Actions runs on every push and pull request to `main`:

- **Test** — pytest across Python 3.11 and 3.12, with Codecov coverage upload
- **Docker** — builds and pushes to `ghcr.io/luong-komorebi/betterstack-monitor-controller` on pushes to `main` and version tags (`v*.*.*`)

The Docker image is published automatically; no extra secrets are needed beyond the default `GITHUB_TOKEN`.

## Versioning

This project follows **Semantic Versioning** (`MAJOR.MINOR.PATCH`) and derives the package version from Git tags.

- Tag format: `vX.Y.Z` (example: `v1.2.3`)
- Source of truth: Git tags (no manual version bump in `pyproject.toml`)
- Docker tags: generated automatically from release tags by CI

### Release flow

1. Merge changes to `main`.
2. Create a version tag (`vX.Y.Z`, for example `v1.2.3`).
3. Push the tag to GitHub.
4. CI builds and publishes a matching container image tag.

## License

[MIT](LICENSE)
