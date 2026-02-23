import importlib
import json
import sys
from types import SimpleNamespace
from unittest.mock import Mock


def load_main(monkeypatch):
    monkeypatch.setenv("BETTERSTACK_API_TOKEN", "test-token")
    sys.modules.pop("main", None)
    return importlib.import_module("main")


def make_patch():
    return SimpleNamespace(metadata=SimpleNamespace(annotations={}))


def test_get_hosts_filters_missing_hosts(monkeypatch):
    main = load_main(monkeypatch)

    spec = {
        "rules": [
            {"host": "api.example.com"},
            {"http": {}},
            {"host": "www.example.com"},
        ]
    }

    assert main._get_hosts(spec) == ["api.example.com", "www.example.com"]


def test_annotation_reads_namespaced_key(monkeypatch):
    main = load_main(monkeypatch)

    annotations = {"betterstack.io/monitor": "true"}
    assert main._annotation(annotations, "monitor") == "true"
    assert main._annotation(annotations, "path", "/api/health") == "/api/health"


def test_on_ingress_skips_when_not_enabled(monkeypatch):
    main = load_main(monkeypatch)
    patch = make_patch()

    main.on_ingress(spec={"rules": [{"host": "example.com"}]}, annotations={}, patch=patch)

    assert patch.metadata.annotations == {}


def test_on_ingress_creates_updates_and_deletes(monkeypatch):
    main = load_main(monkeypatch)
    patch = make_patch()

    client = Mock()
    client.create.return_value = "new-id"
    monkeypatch.setattr(main, "_get_client", lambda: client)

    spec = {"rules": [{"host": "keep.example.com"}, {"host": "new.example.com"}]}
    annotations = {
        "betterstack.io/monitor": "true",
        "betterstack.io/monitor-ids": json.dumps(
            {"keep.example.com": "keep-id", "old.example.com": "old-id"}
        ),
    }

    main.on_ingress(spec=spec, annotations=annotations, patch=patch)

    client.update.assert_called_once_with(
        "keep-id",
        url="https://keep.example.com/api/health",
        name="keep.example.com/api/health",
    )
    client.create.assert_called_once_with(
        url="https://new.example.com/api/health",
        name="new.example.com/api/health",
    )
    client.delete.assert_called_once_with("old-id")

    monitor_ids = json.loads(patch.metadata.annotations["betterstack.io/monitor-ids"])
    assert monitor_ids == {
        "keep.example.com": "keep-id",
        "new.example.com": "new-id",
    }


def test_on_ingress_delete_removes_all_existing_monitors(monkeypatch):
    main = load_main(monkeypatch)

    client = Mock()
    monkeypatch.setattr(main, "_get_client", lambda: client)

    annotations = {
        "betterstack.io/monitor": "true",
        "betterstack.io/monitor-ids": json.dumps(
            {"a.example.com": "id-a", "b.example.com": "id-b"}
        ),
    }

    main.on_ingress_delete(annotations=annotations)

    assert client.delete.call_count == 2
    client.delete.assert_any_call("id-a")
    client.delete.assert_any_call("id-b")
