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

The controller exposes the full configuration surface of the BetterStack monitor API — equivalent to the [`betteruptime_monitor` Terraform resource](https://registry.terraform.io/providers/BetterStackHQ/better-uptime/latest/docs/resources/monitor). Every field is set by adding a `betterstack.io/<field>` annotation to the Ingress.

### Controller annotations

| Annotation | Required | Default | Description |
| ---------- | -------- | ------- | ----------- |
| `betterstack.io/monitor` | Yes | — | Set to `"true"` to enable monitoring |
| `betterstack.io/path` | No | `/api/health` | HTTP path appended to each host to form the monitored URL |
| `betterstack.io/auth-secret` | No | — | Name of a Secret in the Ingress's namespace; reads `username` and `password` keys for HTTP Basic auth (preferred over inline `auth-username` / `auth-password`) |
| `betterstack.io/env-vars-secret` | No | — | Name of a Secret in the Ingress's namespace; all keys are passed as Playwright `environment_variables` (preferred over inline `environment-variables`) |
| `betterstack.io/monitor-ids` | Auto-managed | `{}` | JSON map of host → monitor ID, written back by the controller |

### Monitor configuration annotations

All annotations below map directly to the Terraform provider's `betteruptime_monitor` arguments. Defaults marked **(controller)** are opinionated defaults the controller applies when the annotation is absent; everything else is left unset and Betterstack applies its own server-side default.

| Annotation | Type | Default | Maps to API field |
| ---------- | ---- | ------- | ----------------- |
| `betterstack.io/monitor-type` | string | `expected_status_code` (controller) | `monitor_type` — `status`, `expected_status_code`, `keyword`, `keyword_absence`, `ping`, `tcp`, `udp`, `smtp`, `pop`, `imap`, `dns`, `playwright` |
| `betterstack.io/paused` | bool | — | `paused` |
| `betterstack.io/http-method` | string | `get` (controller) | `http_method` — `GET`, `HEAD`, `POST`, `PUT`, `PATCH` |
| `betterstack.io/request-timeout` | int | `30` (controller) | `request_timeout` (seconds for HTTP; ms for ping/tcp/udp/smtp/pop/imap/dns; seconds for playwright) |
| `betterstack.io/request-body` | string | — | `request_body` (also DNS query domain) |
| `betterstack.io/request-headers` | JSON list of `{name,value}` | — | `request_headers` |
| `betterstack.io/expected-status-codes` | JSON list of int (or comma-separated) | `[200]` (controller) | `expected_status_codes` |
| `betterstack.io/required-keyword` | string | — | `required_keyword` (for `keyword`, `keyword_absence`, `udp`) |
| `betterstack.io/follow-redirects` | bool | `true` (controller) | `follow_redirects` |
| `betterstack.io/remember-cookies` | bool | `true` (controller) | `remember_cookies` |
| `betterstack.io/verify-ssl` | bool | `true` (controller) | `verify_ssl` |
| `betterstack.io/auth-username` | string | — | `auth_username` (sensitive — prefer `auth-secret`) |
| `betterstack.io/auth-password` | string | — | `auth_password` (sensitive — prefer `auth-secret`) |
| `betterstack.io/regions` | JSON list of string (or comma-separated) | `["us"]` (controller) | `regions` — subset of `us`, `eu`, `as`, `au` |
| `betterstack.io/ip-version` | string | — | `ip_version` — `ipv4` or `ipv6` |
| `betterstack.io/port` | string | — | `port` (required for `tcp`, `udp`, `smtp`, `pop`, `imap`) |
| `betterstack.io/proxy-host` | string | — | `proxy_host` (use `user:pass@hostname` for proxy auth) |
| `betterstack.io/proxy-port` | int | — | `proxy_port` |
| `betterstack.io/check-frequency` | int | `300` (controller) | `check_frequency` (seconds) |
| `betterstack.io/confirmation-period` | int | `0` (controller) | `confirmation_period` (seconds) |
| `betterstack.io/recovery-period` | int | `180` (controller) | `recovery_period` (seconds) |
| `betterstack.io/email` | bool | `true` (controller) | `email` |
| `betterstack.io/sms` | bool | — | `sms` |
| `betterstack.io/call` | bool | — | `call` |
| `betterstack.io/push` | bool | — | `push` |
| `betterstack.io/critical-alert` | bool | — | `critical_alert` |
| `betterstack.io/team-wait` | int | — | `team_wait` (seconds before escalating to the team) |
| `betterstack.io/policy-id` | string | — | `policy_id` (escalation policy) |
| `betterstack.io/expiration-policy-id` | int | — | `expiration_policy_id` (SSL/domain expiration escalation policy) |
| `betterstack.io/monitor-group-id` | int | — | `monitor_group_id` |
| `betterstack.io/team-name` | string | — | `team_name` (when using global API tokens) |
| `betterstack.io/ssl-expiration` | int | — | `ssl_expiration` — `1`, `2`, `3`, `7`, `14`, `30`, `60`, or `-1` to disable |
| `betterstack.io/domain-expiration` | int | — | `domain_expiration` — same valid values as `ssl_expiration` |
| `betterstack.io/maintenance-from` | string | — | `maintenance_from` (e.g. `01:00:00`) |
| `betterstack.io/maintenance-to` | string | — | `maintenance_to` (e.g. `03:00:00`) |
| `betterstack.io/maintenance-timezone` | string | — | `maintenance_timezone` (Rails `ActiveSupport::TimeZone` name) |
| `betterstack.io/maintenance-days` | JSON list of string (or comma-separated) | — | `maintenance_days` — subset of `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun` |
| `betterstack.io/playwright-script` | string | — | `playwright_script` (JS source for `playwright` monitor type) |
| `betterstack.io/scenario-name` | string | — | `scenario_name` (Playwright scenario UI label) |
| `betterstack.io/environment-variables` | JSON object of string→string | — | `environment_variables` (sensitive — prefer `env-vars-secret`) |

#### Notes

- **Lists and maps are JSON.** `regions: '["us","eu"]'`, `expected-status-codes: "[200,201]"`, `request-headers: '[{"name":"X-Token","value":"abc"}]'`. For string and integer lists you can also use comma-separated values: `regions: "us,eu"`.
- **Booleans accept** `true`/`false`, `1`/`0`, `yes`/`no` (case-insensitive).
- **Unknown `betterstack.io/*` annotations are ignored** with a log warning.
- **`url` and `pronounceable_name`** are derived by the controller from each Ingress host + `path` and cannot be overridden.
- **Updates reconcile the full payload** — changing any annotation re-applies the full configured state on the next Ingress event.

### Sensitive fields

Three fields are marked sensitive by Betterstack: `auth_username`, `auth_password`, `environment_variables`. Anyone with `get ingresses` RBAC can read annotation values in plaintext, so the controller supports a Secret-reference path:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-app-basic-auth
  namespace: default
type: Opaque
stringData:
  username: probe
  password: super-secret
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app
  annotations:
    betterstack.io/monitor: "true"
    betterstack.io/auth-secret: "my-app-basic-auth"
spec:
  rules:
    - host: my-app.example.com
      # ...
```

Inline `betterstack.io/auth-username` / `betterstack.io/auth-password` / `betterstack.io/environment-variables` annotations also work, but the controller emits a warning every reconcile reminding you they're visible to anyone with read access on the Ingress. Prefer Secret references.

If both an inline annotation and a Secret ref are set for the same field, the Secret wins.

**RBAC.** The controller's ServiceAccount needs `get` on `secrets` in the namespaces it watches. The bundled Helm chart and `k8s/deploy.yaml` already include this permission. If you've configured a custom ClusterRole, add:

```yaml
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get"]
```

### Examples

#### Minimal — defaults only

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

#### Multi-region with custom check frequency, status codes, and headers

```yaml
metadata:
  annotations:
    betterstack.io/monitor: "true"
    betterstack.io/path: "/healthz"
    betterstack.io/regions: '["us","eu","as"]'
    betterstack.io/check-frequency: "60"
    betterstack.io/expected-status-codes: "[200,204]"
    betterstack.io/request-headers: '[{"name":"X-Probe","value":"betterstack"}]'
    betterstack.io/sms: "true"
    betterstack.io/call: "true"
    betterstack.io/team-wait: "300"
```

#### Maintenance window (no checks Mon–Fri 01:00–03:00 UTC)

```yaml
metadata:
  annotations:
    betterstack.io/monitor: "true"
    betterstack.io/maintenance-from: "01:00:00"
    betterstack.io/maintenance-to: "03:00:00"
    betterstack.io/maintenance-timezone: "UTC"
    betterstack.io/maintenance-days: "mon,tue,wed,thu,fri"
```

#### Keyword + SSL/domain expiration alerts

```yaml
metadata:
  annotations:
    betterstack.io/monitor: "true"
    betterstack.io/monitor-type: "keyword"
    betterstack.io/required-keyword: "OK"
    betterstack.io/ssl-expiration: "14"
    betterstack.io/domain-expiration: "30"
```

#### Basic auth via Secret

```yaml
metadata:
  annotations:
    betterstack.io/monitor: "true"
    betterstack.io/auth-secret: "my-app-basic-auth"
```

## Deployment

### Prerequisites

- Kubernetes ≥ 1.24
- A [BetterStack API token](https://betterstack.com/docs/uptime/api/getting-started-with-the-uptime-api/) with monitor read/write permissions

### Helm (recommended)

```bash
# Add the Helm repository (served via GitHub Pages)
helm repo add betterstack-monitor https://luong-komorebi.github.io/betterstack-monitor-controller
helm repo update

# Install
helm upgrade --install betterstack-monitor \
  betterstack-monitor/betterstack-monitor-controller \
  --namespace monitoring \
  --create-namespace \
  --set apiToken=<YOUR_TOKEN>

# Pin a specific chart/app version
helm upgrade --install betterstack-monitor \
  betterstack-monitor/betterstack-monitor-controller \
  --namespace monitoring \
  --create-namespace \
  --set apiToken=<YOUR_TOKEN> \
  --version 0.1.0
```

Or install directly from the local chart:

```bash
helm upgrade --install betterstack-monitor \
  ./helm/betterstack-monitor-controller \
  --namespace monitoring \
  --create-namespace \
  --set apiToken=<YOUR_TOKEN>

# Pin a specific image version
helm upgrade --install betterstack-monitor \
  ./helm/betterstack-monitor-controller \
  --namespace monitoring \
  --create-namespace \
  --set apiToken=<YOUR_TOKEN> \
  --set image.tag=1.2.3

# Reference an existing Secret instead of letting the chart create one
helm upgrade --install betterstack-monitor \
  ./helm/betterstack-monitor-controller \
  --namespace monitoring \
  --create-namespace \
  --set existingSecret.name=my-betterstack-secret \
  --set existingSecret.key=api-token
```

See [`helm/betterstack-monitor-controller/values.yaml`](helm/betterstack-monitor-controller/values.yaml) for all available options.

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
- **Helm lint** — runs `helm lint` on every change to `helm/**`
- **Helm Release** — packages and publishes the chart to the GitHub Pages Helm repo whenever `Chart.yaml` version is bumped on `main`

The Docker image is published automatically; no extra secrets are needed beyond the default `GITHUB_TOKEN`.

## Versioning

This project follows **Semantic Versioning** (`MAJOR.MINOR.PATCH`) and derives the package version from Git tags.

- Tag format: `vX.Y.Z` (example: `v1.2.3`)
- Source of truth: Git tags (no manual version bump in `pyproject.toml`)
- Docker tags: generated automatically from release tags by CI
- Helm chart version (`Chart.yaml` → `version`): bumped independently from the app version when chart templates or values change

### Release flow

#### Application release (Docker image)

1. Merge changes to `main`.
2. Create a version tag (`vX.Y.Z`, for example `v1.2.3`).
3. Push the tag to GitHub.
4. CI builds and publishes a matching container image tag.

#### Helm chart release

1. Update `helm/betterstack-monitor-controller/Chart.yaml` — bump `version` (chart changes) and/or `appVersion` (app version the chart installs by default).
2. Merge to `main`.
3. The **Helm Release** workflow publishes the new chart version to the GitHub Pages Helm repo automatically.

> The `gh-pages` branch and GitHub Pages are bootstrapped automatically by the workflow on first run.

## License

[MIT](LICENSE)
