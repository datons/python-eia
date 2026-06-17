"""
EIA API Client Library

A Python client for interacting with the U.S. Energy Information Administration (EIA) API.
"""

from importlib.metadata import PackageNotFoundError, version as _version

from .client import EIAClient, EIAError
from .cache import CacheConfig
from . import catalog

try:
    __version__ = _version("python-eia")
except PackageNotFoundError:  # not installed (e.g. running from a source checkout)
    __version__ = "0.0.0+unknown"
__all__ = ["EIAClient", "EIAError", "CacheConfig", "catalog"]
