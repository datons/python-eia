"""CLI command: list facet values for a data endpoint."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def facets_command(
    route: str = typer.Argument(..., help="Route path to a data endpoint"),
    facet_id: str = typer.Argument(..., help="Facet ID to list values for (e.g. 'respondent', 'fueltype')"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, csv, json"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="EIA API key"),
):
    """List available values for a facet on a data endpoint.

    \b
    Examples:
        eia facets electricity/rto/fuel-type-data respondent
        eia facets electricity/rto/fuel-type-data fueltype --format csv
    """
    from eia.cli.app import get_client

    client = get_client(api_key)

    response = client.get_facet_values(route, facet_id)
    facet_values = response.get("facets", [])

    if not facet_values:
        typer.echo(f"No values found for facet '{facet_id}' at '{route}'.")
        raise typer.Exit(0)

    if format == "json":
        import json

        text = json.dumps(facet_values, indent=2)
        if output:
            from pathlib import Path
            Path(output).write_text(text)
            typer.echo(f"Written to {output}")
        else:
            typer.echo(text)
        return

    if format == "csv":
        lines = ["id,name"]
        for v in facet_values:
            name = (v.get("name") or "").replace(",", ";")
            lines.append(f"{v['id']},{name}")
        text = "\n".join(lines)
        if output:
            from pathlib import Path
            Path(output).write_text(text)
            typer.echo(f"Written to {output}")
        else:
            typer.echo(text)
        return

    # Rich table
    table = Table(title=f"Facet: {facet_id}")
    table.add_column("ID", style="cyan")
    table.add_column("Name")

    for v in facet_values:
        table.add_row(v.get("id", ""), v.get("name", ""))

    console.print(table)
