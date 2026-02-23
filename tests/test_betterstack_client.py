from unittest.mock import Mock

import pytest

import betterstack_client
from betterstack_client import BetterstackClient, MONITOR_DEFAULTS


class DummySession:
    def __init__(self):
        self.headers = {}


def test_client_sets_authorization_header(monkeypatch):
    dummy = DummySession()
    monkeypatch.setattr(betterstack_client.requests, "Session", lambda: dummy)

    BetterstackClient("secret-token")

    assert dummy.headers["Authorization"] == "Bearer secret-token"


def test_create_posts_with_defaults_and_returns_monitor_id():
    client = BetterstackClient("token")

    response = Mock()
    response.json.return_value = {"data": {"id": "monitor-123"}}
    response.raise_for_status = Mock()
    client.session.post = Mock(return_value=response)

    result = client.create(url="https://example.com/health", name="example")

    assert result == "monitor-123"

    client.session.post.assert_called_once()
    url, = client.session.post.call_args[0]
    payload = client.session.post.call_args.kwargs["json"]

    assert url == f"{betterstack_client.BASE_URL}/monitors"
    assert payload["url"] == "https://example.com/health"
    assert payload["pronounceable_name"] == "example"
    for key, value in MONITOR_DEFAULTS.items():
        assert payload[key] == value


def test_update_patches_monitor_and_checks_status():
    client = BetterstackClient("token")

    response = Mock()
    response.raise_for_status = Mock()
    client.session.patch = Mock(return_value=response)

    client.update("monitor-1", url="https://example.com", name="example")

    client.session.patch.assert_called_once_with(
        f"{betterstack_client.BASE_URL}/monitors/monitor-1",
        json={"url": "https://example.com", "pronounceable_name": "example"},
    )
    response.raise_for_status.assert_called_once()


def test_delete_ignores_404():
    client = BetterstackClient("token")

    response = Mock(status_code=404)
    response.raise_for_status = Mock()
    client.session.delete = Mock(return_value=response)

    client.delete("missing-monitor")

    response.raise_for_status.assert_not_called()


def test_delete_raises_for_non_404_error():
    client = BetterstackClient("token")

    response = Mock(status_code=500)
    response.raise_for_status.side_effect = RuntimeError("HTTP 500")
    client.session.delete = Mock(return_value=response)

    with pytest.raises(RuntimeError, match="HTTP 500"):
        client.delete("broken-monitor")
