"""
EIA API Client Library

A Python client for interacting with the U.S. Energy Information Administration (EIA) API.
"""

from .client import EIAClient, EIAError

__version__ = "0.1.0"
__all__ = ["EIAClient", "EIAError"]
