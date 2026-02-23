"""
Shared fixtures and test configuration.

BETTERSTACK_API_TOKEN must be present before `main` is imported (it is read at
module level).  Setting it here — before any test module is collected — ensures
the import succeeds without touching real credentials.
"""

import os

import pytest

# Ensure the env-var is available for module-level import in main.py
os.environ.setdefault("BETTERSTACK_API_TOKEN", "test-token-fixture")


@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    """Keep BETTERSTACK_API_TOKEN stable across every test."""
    monkeypatch.setenv("BETTERSTACK_API_TOKEN", "test-token-fixture")
