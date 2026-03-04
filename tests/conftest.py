"""Shared fixtures for EIA tests."""

import os

import pytest


def _load_env():
    """Load .env file if present."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k, v)


_load_env()


@pytest.fixture(scope="session")
def client():
    """Shared EIA client instance."""
    from eia.client import EIAClient
    return EIAClient()


@pytest.fixture(scope="session")
def data_endpoint(client):
    """Pre-loaded Data object for electricity/rto/fuel-type-data."""
    return client.get_data_endpoint("electricity/rto/fuel-type-data")
