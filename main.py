import json
import logging
import os

import kopf

from betterstack_client import BetterstackClient

log = logging.getLogger(__name__)
API_TOKEN = os.environ["BETTERSTACK_API_TOKEN"]


def _get_client():
    return BetterstackClient(API_TOKEN)


def _get_hosts(spec):
    return [rule["host"] for rule in (spec.get("rules") or []) if rule.get("host")]


def _annotation(annotations, key, default=None):
    return annotations.get(f"betterstack.io/{key}", default)


@kopf.on.create("networking.k8s.io", "v1", "ingresses")
@kopf.on.update("networking.k8s.io", "v1", "ingresses")
def on_ingress(spec, annotations, patch, **kwargs):
    if _annotation(annotations, "monitor") != "true":
        return

    path = _annotation(annotations, "path", "/api/health")
    hosts = _get_hosts(spec)
    if not hosts:
        return

    client = _get_client()
    existing = json.loads(_annotation(annotations, "monitor-ids", "{}"))
    monitor_ids = {}

    for host in hosts:
        url = f"https://{host}{path}"
        name = f"{host}{path}"
        if host in existing:
            client.update(existing[host], url=url, name=name)
            monitor_ids[host] = existing[host]
            log.info(f"Updated monitor {existing[host]} for {url}")
        else:
            mid = client.create(url=url, name=name)
            monitor_ids[host] = mid
            log.info(f"Created monitor {mid} for {url}")

    # Remove monitors for hosts no longer in the Ingress
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
