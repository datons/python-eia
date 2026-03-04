"""EIA CLI — command-line interface for the EIA API."""

try:
    from eia.cli.app import app
except ImportError:
    raise ImportError(
        "CLI dependencies not installed. Install with: pip install python-eia"
    )

__all__ = ["app"]
