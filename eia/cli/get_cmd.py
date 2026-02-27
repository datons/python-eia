"""CLI command: fetch data from a data endpoint."""

from __future__ import annotations

from typing import Optional

import typer

from eia.cli._output import render_dataframe


def _parse_facets(facet_args: list[str]) -> dict[str, str | list[str]]:
    """Parse --facet key=value arguments into a dict.

    Multiple values for the same key are collected into a list.
    """
    facets: dict[str, str | list[str]] = {}
    for arg in facet_args:
        if "=" not in arg:
            typer.echo(f"Error: Invalid facet format '{arg}'. Use key=value.", err=True)
            raise typer.Exit(1)
        key, value = arg.split("=", 1)
        if key in facets:
            existing = facets[key]
            if isinstance(existing, list):
                existing.append(value)
            else:
                facets[key] = [existing, value]
        else:
            facets[key] = value
    return facets


def get_command(
    route: str = typer.Argument(..., help="Route path to a data endpoint"),
    start: Optional[str] = typer.Option(None, "--start", "-s", help="Start date (e.g. 2024-01-01)"),
    end: Optional[str] = typer.Option(None, "--end", "-e", help="End date (e.g. 2024-01-31)"),
    frequency: Optional[str] = typer.Option(None, "--frequency", help="Data frequency (e.g. hourly, monthly)"),
    facet: Optional[list[str]] = typer.Option(None, "--facet", help="Facet filter as key=value (repeatable)"),
    data: Optional[list[str]] = typer.Option(None, "--data", "-d", help="Data column to include (repeatable)"),
    sort_col: Optional[str] = typer.Option(None, "--sort", help="Sort column"),
    sort_dir: str = typer.Option("asc", "--sort-dir", help="Sort direction: asc or desc"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, csv, json"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="EIA API key"),
):
    """Fetch data from an EIA data endpoint.

    \b
    Examples:
        eia get electricity/rto/fuel-type-data \\
          --start 2024-06-01 --end 2024-06-08 \\
          --frequency hourly \\
          --facet respondent=CISO \\
          --data value

        eia get petroleum/pri/spt --start 2024-01-01 --end 2024-06-01 \\
          --format csv --output prices.csv
    """
    from eia.cli.app import get_client

    client = get_client(api_key)

    # Build the Data object
    data_endpoint = client.get_data_endpoint(route)

    # Parse facets
    facets = _parse_facets(facet) if facet else None

    # Sort
    sort = None
    if sort_col:
        sort = [{"column": sort_col, "direction": sort_dir}]

    # Fetch
    df = data_endpoint.get(
        data_columns=data or None,
        facets=facets,
        frequency=frequency,
        start=start,
        end=end,
        sort=sort,
    )

    if df.empty:
        typer.echo("No data returned.")
        raise typer.Exit(0)

    render_dataframe(df, format=format, output=output)
