import requests

BASE_URL = "https://uptime.betterstack.com/api/v2"

MONITOR_DEFAULTS = {
    "monitor_type": "expected_status_code",
    "expected_status_codes": [200],
    "check_frequency": 300,
    "regions": ["us"],
    "email": True,
    "verify_ssl": True,
    "follow_redirects": True,
    "remember_cookies": True,
    "recovery_period": 180,
    "confirmation_period": 0,
    "request_timeout": 30,
    "http_method": "get",
}


class BetterstackClient:
    def __init__(self, token):
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"

    def create(self, url, name):
        resp = self.session.post(
            f"{BASE_URL}/monitors",
            json={"url": url, "pronounceable_name": name, **MONITOR_DEFAULTS},
        )
        resp.raise_for_status()
        return resp.json()["data"]["id"]

    def update(self, monitor_id, url, name):
        resp = self.session.patch(
            f"{BASE_URL}/monitors/{monitor_id}",
            json={"url": url, "pronounceable_name": name},
        )
        resp.raise_for_status()

    def delete(self, monitor_id):
        resp = self.session.delete(f"{BASE_URL}/monitors/{monitor_id}")
        if resp.status_code != 404:
            resp.raise_for_status()
