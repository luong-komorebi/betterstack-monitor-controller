"""Tests for BetterstackClient."""

import pytest
import requests
from unittest.mock import MagicMock, patch

from betterstack_client import BetterstackClient, BASE_URL, MONITOR_DEFAULTS


@pytest.fixture
def client():
    return BetterstackClient(token="test-token")


class TestBetterstackClientInit:
    def test_auth_header_set(self, client):
        assert client.session.headers["Authorization"] == "Bearer test-token"


class TestCreate:
    def test_returns_monitor_id(self, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"id": "abc123"}}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client.session, "post", return_value=mock_resp) as mock_post:
            result = client.create(url="https://example.com/health", name="example.com/health")

        assert result == "abc123"
        mock_post.assert_called_once_with(
            f"{BASE_URL}/monitors",
            json={
                "url": "https://example.com/health",
                "pronounceable_name": "example.com/health",
                **MONITOR_DEFAULTS,
            },
        )

    def test_raises_on_http_error(self, client):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("400 Bad Request")

        with patch.object(client.session, "post", return_value=mock_resp):
            with pytest.raises(requests.HTTPError):
                client.create(url="https://bad.example.com", name="bad")


class TestUpdate:
    def test_patches_correct_endpoint(self, client):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client.session, "patch", return_value=mock_resp) as mock_patch:
            client.update("mon-42", url="https://example.com/health", name="example.com/health")

        mock_patch.assert_called_once_with(
            f"{BASE_URL}/monitors/mon-42",
            json={"url": "https://example.com/health", "pronounceable_name": "example.com/health"},
        )
        mock_resp.raise_for_status.assert_called_once()

    def test_raises_on_http_error(self, client):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500 Server Error")

        with patch.object(client.session, "patch", return_value=mock_resp):
            with pytest.raises(requests.HTTPError):
                client.update("mon-99", url="https://example.com", name="example.com")


class TestDelete:
    def test_deletes_correct_endpoint(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client.session, "delete", return_value=mock_resp) as mock_del:
            client.delete("mon-42")

        mock_del.assert_called_once_with(f"{BASE_URL}/monitors/mon-42")
        mock_resp.raise_for_status.assert_called_once()

    def test_ignores_404(self, client):
        """Deleting a monitor that no longer exists should not raise."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client.session, "delete", return_value=mock_resp):
            client.delete("non-existent")  # should not raise

        mock_resp.raise_for_status.assert_not_called()

    def test_raises_on_other_http_error(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500 Server Error")

        with patch.object(client.session, "delete", return_value=mock_resp):
            with pytest.raises(requests.HTTPError):
                client.delete("mon-42")
