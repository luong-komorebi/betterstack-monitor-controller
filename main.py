import base64
import json
import logging
import os

import kopf

from betterstack_client import BetterstackClient
from monitor_fields import (
    ANNOTATION_TO_FIELD,
    SENSITIVE_FIELDS,
    FieldCoercionError,
    coerce,
)

log = logging.getLogger(__name__)
API_TOKEN = os.environ["BETTERSTACK_API_TOKEN"]
ANNOTATION_PREFIX = "betterstack.io/"

# Annotations the controller manages itself — never treated as monitor config.
RESERVED_ANNOTATIONS = frozenset({"monitor", "path", "monitor-ids", "auth-secret", "env-vars-secret"})


def _get_client():
    return BetterstackClient(API_TOKEN)


def _get_kube_core_v1():
    from kubernetes import client, config

    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CoreV1Api()


def _get_hosts(spec):
    return [rule["host"] for rule in (spec.get("rules") or []) if rule.get("host")]


def _annotation(annotations, key, default=None):
    return annotations.get(f"{ANNOTATION_PREFIX}{key}", default)


def _read_secret(namespace, name):
    api = _get_kube_core_v1()
    secret = api.read_namespaced_secret(name=name, namespace=namespace)
    return {
        key: base64.b64decode(value).decode("utf-8")
        for key, value in (secret.data or {}).items()
    }


def _resolve_sensitive_fields(annotations, namespace):
    """Resolve auth + env-vars from referenced Secrets, falling back to inline annotations.

    Inline values still work but emit a warning — Secret refs are the recommended path.
    Returns a dict of {api_field_name: value}.
    """
    resolved = {}

    auth_secret = _annotation(annotations, "auth-secret")
    if auth_secret:
        data = _read_secret(namespace, auth_secret)
        if "username" in data:
            resolved["auth_username"] = data["username"]
        if "password" in data:
            resolved["auth_password"] = data["password"]

    env_secret = _annotation(annotations, "env-vars-secret")
    if env_secret:
        resolved["environment_variables"] = _read_secret(namespace, env_secret)

    return resolved


def _build_monitor_config(annotations, namespace):
    """Translate annotations into a BetterStack monitor payload.

    Unknown `betterstack.io/*` annotations are logged and ignored.
    Inline sensitive annotations are accepted with a warning; Secret refs override them.
    """
    config = {}
    inline_sensitive = []

    for key, raw in annotations.items():
        if not key.startswith(ANNOTATION_PREFIX):
            continue
        suffix = key[len(ANNOTATION_PREFIX):]
        if suffix in RESERVED_ANNOTATIONS:
            continue
        mapping = ANNOTATION_TO_FIELD.get(suffix)
        if mapping is None:
            log.warning(f"Ignoring unknown annotation {key!r}")
            continue
        api_name, kind = mapping
        try:
            config[api_name] = coerce(key, kind, raw)
        except FieldCoercionError as exc:
            log.error(str(exc))
            continue
        if api_name in SENSITIVE_FIELDS:
            inline_sensitive.append(key)

    if inline_sensitive:
        log.warning(
            "Sensitive fields configured inline via annotations: %s. "
            "Anyone with read access to this Ingress can see these values. "
            "Consider 'betterstack.io/auth-secret' or 'betterstack.io/env-vars-secret' instead.",
            ", ".join(sorted(inline_sensitive)),
        )

    config.update(_resolve_sensitive_fields(annotations, namespace))
    return config


@kopf.on.create("networking.k8s.io", "v1", "ingresses")
@kopf.on.update("networking.k8s.io", "v1", "ingresses")
def on_ingress(spec, annotations, namespace, patch, **kwargs):
    if _annotation(annotations, "monitor") != "true":
        return

    path = _annotation(annotations, "path", "/api/health")
    hosts = _get_hosts(spec)
    if not hosts:
        return

    config = _build_monitor_config(annotations, namespace)
    client = _get_client()
    existing = json.loads(_annotation(annotations, "monitor-ids", "{}"))
    monitor_ids = {}

    for host in hosts:
        url = f"https://{host}{path}"
        name = f"{host}{path}"
        if host in existing:
            client.update(existing[host], url=url, name=name, **config)
            monitor_ids[host] = existing[host]
            log.info(f"Updated monitor {existing[host]} for {url}")
        else:
            mid = client.create(url=url, name=name, **config)
            monitor_ids[host] = mid
            log.info(f"Created monitor {mid} for {url}")

    for host, mid in existing.items():
        if host not in monitor_ids:
            client.delete(mid)
            log.info(f"Deleted monitor {mid} for removed host {host}")

    patch.metadata.annotations["betterstack.io/monitor-ids"] = json.dumps(monitor_ids)


@kopf.on.delete("networking.k8s.io", "v1", "ingresses")
def on_ingress_delete(annotations, **kwargs):
    if _annotation(annotations, "monitor") != "true":
        return

    existing = json.loads(_annotation(annotations, "monitor-ids", "{}"))
    client = _get_client()
    for host, mid in existing.items():
        client.delete(mid)
        log.info(f"Deleted monitor {mid} for {host}")
