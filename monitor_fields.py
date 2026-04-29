"""Mapping between Kubernetes annotations and BetterStack monitor API fields.

Mirrors the configurable surface of the `betteruptime_monitor` Terraform
resource: https://registry.terraform.io/providers/BetterStackHQ/better-uptime/latest/docs/resources/monitor

Each field has:
    annotation : kebab-case suffix used after the `betterstack.io/` prefix
    api_name   : snake_case key sent to the BetterStack API
    kind       : type coercion applied to the annotation value

Coercion kinds:
    str       — kept as-is
    int       — int(value)
    bool      — case-insensitive "true"/"false"/"1"/"0"/"yes"/"no"
    list_str  — JSON array of strings, or a comma-separated string
    list_int  — JSON array of integers, or a comma-separated string
    list_map  — JSON array of objects (e.g. request_headers)
    map_str   — JSON object of string→string (e.g. environment_variables)
"""

import json


SENSITIVE_FIELDS = frozenset({"auth_username", "auth_password", "environment_variables"})


# (annotation suffix, API field name, coercion kind)
MONITOR_FIELDS = (
    # Core
    ("monitor-type", "monitor_type", "str"),
    ("paused", "paused", "bool"),
    # HTTP request shape
    ("http-method", "http_method", "str"),
    ("request-timeout", "request_timeout", "int"),
    ("request-body", "request_body", "str"),
    ("request-headers", "request_headers", "list_map"),
    ("expected-status-codes", "expected_status_codes", "list_int"),
    ("required-keyword", "required_keyword", "str"),
    ("follow-redirects", "follow_redirects", "bool"),
    ("remember-cookies", "remember_cookies", "bool"),
    ("verify-ssl", "verify_ssl", "bool"),
    # Auth
    ("auth-username", "auth_username", "str"),
    ("auth-password", "auth_password", "str"),
    # Network
    ("regions", "regions", "list_str"),
    ("ip-version", "ip_version", "str"),
    ("port", "port", "str"),
    ("proxy-host", "proxy_host", "str"),
    ("proxy-port", "proxy_port", "int"),
    # Timing / incidents
    ("check-frequency", "check_frequency", "int"),
    ("confirmation-period", "confirmation_period", "int"),
    ("recovery-period", "recovery_period", "int"),
    # Alert channels
    ("email", "email", "bool"),
    ("sms", "sms", "bool"),
    ("call", "call", "bool"),
    ("push", "push", "bool"),
    ("critical-alert", "critical_alert", "bool"),
    ("team-wait", "team_wait", "int"),
    # Escalation / grouping
    ("policy-id", "policy_id", "str"),
    ("expiration-policy-id", "expiration_policy_id", "int"),
    ("monitor-group-id", "monitor_group_id", "int"),
    ("team-name", "team_name", "str"),
    # Expiration checks
    ("ssl-expiration", "ssl_expiration", "int"),
    ("domain-expiration", "domain_expiration", "int"),
    # Maintenance window
    ("maintenance-from", "maintenance_from", "str"),
    ("maintenance-to", "maintenance_to", "str"),
    ("maintenance-timezone", "maintenance_timezone", "str"),
    ("maintenance-days", "maintenance_days", "list_str"),
    # Playwright
    ("playwright-script", "playwright_script", "str"),
    ("scenario-name", "scenario_name", "str"),
    ("environment-variables", "environment_variables", "map_str"),
)

ANNOTATION_TO_FIELD = {ann: (api, kind) for ann, api, kind in MONITOR_FIELDS}


_BOOL_TRUE = {"true", "1", "yes"}
_BOOL_FALSE = {"false", "0", "no"}


class FieldCoercionError(ValueError):
    """Raised when an annotation value cannot be coerced to the field type."""


def _coerce_bool(annotation, raw):
    value = raw.strip().lower()
    if value in _BOOL_TRUE:
        return True
    if value in _BOOL_FALSE:
        return False
    raise FieldCoercionError(f"annotation {annotation!r}: expected boolean, got {raw!r}")


def _coerce_int(annotation, raw):
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise FieldCoercionError(f"annotation {annotation!r}: expected integer, got {raw!r}") from exc


def _coerce_json(annotation, raw, expected_label):
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FieldCoercionError(
            f"annotation {annotation!r}: expected JSON {expected_label}, got {raw!r}"
        ) from exc


def _coerce_list_str(annotation, raw):
    stripped = raw.strip()
    if stripped.startswith("["):
        value = _coerce_json(annotation, raw, "array of strings")
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise FieldCoercionError(
                f"annotation {annotation!r}: expected JSON array of strings, got {raw!r}"
            )
        return value
    return [item.strip() for item in stripped.split(",") if item.strip()]


def _coerce_list_int(annotation, raw):
    stripped = raw.strip()
    if stripped.startswith("["):
        value = _coerce_json(annotation, raw, "array of integers")
        if not isinstance(value, list) or not all(isinstance(v, int) and not isinstance(v, bool) for v in value):
            raise FieldCoercionError(
                f"annotation {annotation!r}: expected JSON array of integers, got {raw!r}"
            )
        return value
    try:
        return [int(item.strip()) for item in stripped.split(",") if item.strip()]
    except ValueError as exc:
        raise FieldCoercionError(
            f"annotation {annotation!r}: expected comma-separated integers, got {raw!r}"
        ) from exc


def _coerce_list_map(annotation, raw):
    value = _coerce_json(annotation, raw, "array of objects")
    if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
        raise FieldCoercionError(
            f"annotation {annotation!r}: expected JSON array of objects, got {raw!r}"
        )
    return value


def _coerce_map_str(annotation, raw):
    value = _coerce_json(annotation, raw, "object of strings")
    if not isinstance(value, dict) or not all(isinstance(v, str) for v in value.values()):
        raise FieldCoercionError(
            f"annotation {annotation!r}: expected JSON object of strings, got {raw!r}"
        )
    return value


_COERCERS = {
    "str": lambda ann, raw: raw,
    "int": _coerce_int,
    "bool": _coerce_bool,
    "list_str": _coerce_list_str,
    "list_int": _coerce_list_int,
    "list_map": _coerce_list_map,
    "map_str": _coerce_map_str,
}


def coerce(annotation, kind, raw):
    """Coerce a raw annotation string to the type required by the API field."""
    return _COERCERS[kind](annotation, raw)
