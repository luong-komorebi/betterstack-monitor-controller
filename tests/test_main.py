import importlib
import json
import logging
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

    main.on_ingress(
        spec={"rules": [{"host": "example.com"}]},
        annotations={},
        namespace="default",
        patch=patch,
    )

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

    main.on_ingress(spec=spec, annotations=annotations, namespace="default", patch=patch)

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


# ── monitor configuration via annotations ────────────────────────────────────


def test_build_monitor_config_parses_typed_annotations(monkeypatch):
    main = load_main(monkeypatch)

    annotations = {
        "betterstack.io/monitor": "true",
        "betterstack.io/check-frequency": "60",
        "betterstack.io/regions": '["us","eu"]',
        "betterstack.io/expected-status-codes": "200, 204",
        "betterstack.io/follow-redirects": "false",
        "betterstack.io/request-headers": '[{"name":"X-Probe","value":"a"}]',
        # Reserved annotations are ignored as monitor config:
        "betterstack.io/path": "/healthz",
        "betterstack.io/monitor-ids": "{}",
    }

    config = main._build_monitor_config(annotations, namespace="default")

    assert config == {
        "check_frequency": 60,
        "regions": ["us", "eu"],
        "expected_status_codes": [200, 204],
        "follow_redirects": False,
        "request_headers": [{"name": "X-Probe", "value": "a"}],
    }


def test_build_monitor_config_logs_unknown_annotation(monkeypatch, caplog):
    main = load_main(monkeypatch)

    annotations = {"betterstack.io/totally-bogus": "value"}

    with caplog.at_level(logging.WARNING, logger="main"):
        config = main._build_monitor_config(annotations, namespace="default")

    assert config == {}
    assert any("totally-bogus" in record.message for record in caplog.records)


def test_build_monitor_config_logs_coercion_error(monkeypatch, caplog):
    main = load_main(monkeypatch)

    annotations = {"betterstack.io/check-frequency": "not-a-number"}

    with caplog.at_level(logging.ERROR, logger="main"):
        config = main._build_monitor_config(annotations, namespace="default")

    assert "check_frequency" not in config
    assert any("check-frequency" in record.message for record in caplog.records)


def test_build_monitor_config_warns_on_inline_sensitive(monkeypatch, caplog):
    main = load_main(monkeypatch)

    annotations = {
        "betterstack.io/auth-username": "probe",
        "betterstack.io/auth-password": "secret",
    }

    with caplog.at_level(logging.WARNING, logger="main"):
        config = main._build_monitor_config(annotations, namespace="default")

    assert config["auth_username"] == "probe"
    assert config["auth_password"] == "secret"
    warning_msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("auth-username" in msg and "auth-password" in msg for msg in warning_msgs)


def test_build_monitor_config_resolves_auth_secret(monkeypatch):
    main = load_main(monkeypatch)

    monkeypatch.setattr(
        main,
        "_read_secret",
        lambda ns, name: {"username": "from-secret", "password": "shh"},
    )

    annotations = {"betterstack.io/auth-secret": "auth"}
    config = main._build_monitor_config(annotations, namespace="default")

    assert config["auth_username"] == "from-secret"
    assert config["auth_password"] == "shh"


def test_auth_secret_overrides_inline_annotation(monkeypatch):
    main = load_main(monkeypatch)

    monkeypatch.setattr(
        main,
        "_read_secret",
        lambda ns, name: {"username": "from-secret", "password": "from-secret-pw"},
    )

    annotations = {
        "betterstack.io/auth-username": "inline",
        "betterstack.io/auth-password": "inline-pw",
        "betterstack.io/auth-secret": "auth",
    }
    config = main._build_monitor_config(annotations, namespace="default")

    assert config["auth_username"] == "from-secret"
    assert config["auth_password"] == "from-secret-pw"


def test_build_monitor_config_resolves_env_vars_secret(monkeypatch):
    main = load_main(monkeypatch)

    monkeypatch.setattr(
        main,
        "_read_secret",
        lambda ns, name: {"FOO": "bar", "BAZ": "qux"},
    )

    annotations = {"betterstack.io/env-vars-secret": "playwright-env"}
    config = main._build_monitor_config(annotations, namespace="default")

    assert config["environment_variables"] == {"FOO": "bar", "BAZ": "qux"}


def test_on_ingress_passes_config_to_client_on_create(monkeypatch):
    main = load_main(monkeypatch)
    patch = make_patch()

    client = Mock()
    client.create.return_value = "new-id"
    monkeypatch.setattr(main, "_get_client", lambda: client)

    annotations = {
        "betterstack.io/monitor": "true",
        "betterstack.io/check-frequency": "60",
        "betterstack.io/regions": "us,eu",
        "betterstack.io/sms": "true",
    }
    spec = {"rules": [{"host": "api.example.com"}]}

    main.on_ingress(spec=spec, annotations=annotations, namespace="default", patch=patch)

    client.create.assert_called_once_with(
        url="https://api.example.com/api/health",
        name="api.example.com/api/health",
        check_frequency=60,
        regions=["us", "eu"],
        sms=True,
    )


def test_on_ingress_passes_config_to_client_on_update(monkeypatch):
    main = load_main(monkeypatch)
    patch = make_patch()

    client = Mock()
    monkeypatch.setattr(main, "_get_client", lambda: client)

    annotations = {
        "betterstack.io/monitor": "true",
        "betterstack.io/check-frequency": "30",
        "betterstack.io/monitor-ids": json.dumps({"api.example.com": "existing-id"}),
    }
    spec = {"rules": [{"host": "api.example.com"}]}

    main.on_ingress(spec=spec, annotations=annotations, namespace="default", patch=patch)

    client.update.assert_called_once_with(
        "existing-id",
        url="https://api.example.com/api/health",
        name="api.example.com/api/health",
        check_frequency=30,
    )
