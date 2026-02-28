"""EIA CLI — main Typer application."""

from __future__ import annotations

import logging

import typer

from eia.cli.config import get_api_key

# Suppress the library's default INFO logging in CLI mode
logging.getLogger().setLevel(logging.WARNING)

app = typer.Typer(
    name="eia",
    help="CLI for the U.S. Energy Information Administration (EIA) API v2.",
    no_args_is_help=True,
)


def get_client(api_key: str | None = None):
    """Lazy import + construct client."""
    from eia.client import EIAClient

    resolved = api_key or get_api_key()
    if not resolved:
        typer.echo(
            "Error: No API key. Set EIA_API_KEY or run: eia config set api-key <KEY>",
            err=True,
        )
        raise typer.Exit(1)
    return EIAClient(api_key=resolved)


# -- Register commands --------------------------------------------------------

from eia.cli.routes_cmd import routes_command  # noqa: E402
from eia.cli.meta_cmd import meta_command  # noqa: E402
from eia.cli.facets_cmd import facets_command  # noqa: E402
from eia.cli.get_cmd import get_command  # noqa: E402
from eia.cli.exec_cmd import exec_command  # noqa: E402
from eia.cli.config_cmd import config_app  # noqa: E402
from eia.cli.cache_cmd import cache_app  # noqa: E402

app.command(name="routes")(routes_command)
app.command(name="meta")(meta_command)
app.command(name="facets")(facets_command)
app.command(name="get")(get_command)
app.command(name="exec")(exec_command)
app.add_typer(config_app, name="config", help="Configuration management")
app.add_typer(cache_app, name="cache", help="Cache management")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
