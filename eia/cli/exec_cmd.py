"""CLI command: fetch data and evaluate a pandas expression."""

from __future__ import annotations

from typing import Optional

import typer

from eia.cli._output import render_result
from eia.cli.get_cmd import _parse_facets


def exec_command(
    route: str = typer.Argument(..., help="Route path to a data endpoint"),
    start: Optional[str] = typer.Option(None, "--start", "-s", help="Start date (e.g. 2024-01-01)"),
    end: Optional[str] = typer.Option(None, "--end", "-e", help="End date (e.g. 2024-01-31)"),
    frequency: Optional[str] = typer.Option(None, "--frequency", help="Data frequency (e.g. hourly, monthly)"),
    facet: Optional[list[str]] = typer.Option(None, "--facet", help="Facet filter as key=value (repeatable)"),
    data: Optional[list[str]] = typer.Option(None, "--data", "-d", help="Data column to include (repeatable)"),
    expr: str = typer.Option("df", "--expr", "-x", help="Python expression to evaluate (df, pd, np available)"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, csv, json"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="EIA API key"),
):
    """Fetch data and evaluate a Python expression on it.

    The fetched data is available as `df` (pandas DataFrame).
    `pd` (pandas) and `np` (numpy) are also available.

    \b
    Examples:
        eia exec electricity/rto/fuel-type-data \\
          --start 2024-06-01 --end 2024-06-08 \\
          --frequency hourly \\
          --facet respondent=CISO --data value \\
          -x "df.groupby('fueltype')['value'].mean()"

        eia exec electricity/rto/fuel-type-data \\
          --start 2024-06-01 --end 2024-06-03 \\
          --frequency hourly \\
          --facet respondent=CISO --data value \\
          -x "df.describe()"
    """
    import numpy as np
    import pandas as pd

    from eia.cli.app import get_client

    client = get_client(api_key)

    # Build the Data object
    data_endpoint = client.get_data_endpoint(route)

    # Parse facets
    facets = _parse_facets(facet) if facet else None

    # Fetch
    df = data_endpoint.get(
        data_columns=data or None,
        facets=facets,
        frequency=frequency,
        start=start,
        end=end,
    )

    if df.empty:
        typer.echo("No data returned.")
        raise typer.Exit(0)

    # Evaluate expression
    namespace = {"df": df, "pd": pd, "np": np}
    try:
        result = eval(expr, {"__builtins__": {}}, namespace)  # noqa: S307
    except Exception as exc:
        typer.echo(f"Error evaluating expression: {exc}", err=True)
        raise typer.Exit(1)

    render_result(result, format=format, output=output)
