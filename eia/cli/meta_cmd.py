"""CLI command: inspect a data endpoint's metadata."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def meta_command(
    route: str = typer.Argument(..., help="Route path to a data endpoint (e.g. 'electricity/rto/fuel-type-data')"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="EIA API key"),
):
    """Show facets, frequencies, and data columns for a data endpoint.

    \b
    Examples:
        eia meta electricity/rto/fuel-type-data
        eia meta petroleum/pri/spt --format json
    """
    from eia.cli.app import get_client

    client = get_client(api_key)

    metadata = client.get_metadata(route)

    if "routes" in metadata and "facets" not in metadata:
        typer.echo(f"'{route}' is not a data endpoint — it has child routes.")
        typer.echo("Use 'eia routes' to explore, or navigate deeper.")
        raise typer.Exit(1)

    if format == "json":
        import json

        typer.echo(json.dumps(metadata, indent=2))
        return

    # --- Rich formatted output ---

    name = metadata.get("name", route)
    description = metadata.get("description", "")
    start_period = metadata.get("startPeriod", "?")
    end_period = metadata.get("endPeriod", "?")
    default_freq = metadata.get("defaultFrequency", "?")

    header = f"[bold]{name}[/bold]\n{description}\n\nPeriod: {start_period} → {end_period}  |  Default frequency: {default_freq}"
    console.print(Panel(header, title=f"[cyan]{route}[/cyan]"))

    # Frequencies
    freqs = metadata.get("frequency", [])
    if freqs:
        freq_table = Table(title="Frequencies")
        freq_table.add_column("ID", style="cyan")
        freq_table.add_column("Description")
        freq_table.add_column("Format")
        for f in freqs:
            if isinstance(f, dict):
                freq_table.add_row(f.get("id", ""), f.get("description", ""), f.get("format", ""))
        console.print(freq_table)

    # Facets
    facets = metadata.get("facets", [])
    if facets:
        facet_table = Table(title="Facets")
        facet_table.add_column("ID", style="cyan")
        facet_table.add_column("Description")
        for fct in facets:
            if isinstance(fct, dict):
                facet_table.add_row(fct.get("id", ""), fct.get("description", ""))
        console.print(facet_table)

    # Data columns
    data_cols = metadata.get("data", {})
    if data_cols:
        col_table = Table(title="Data Columns")
        col_table.add_column("ID", style="cyan")
        col_table.add_column("Alias")
        col_table.add_column("Units")
        for col_id, col_data in data_cols.items():
            if isinstance(col_data, dict):
                col_table.add_row(
                    col_id,
                    col_data.get("alias", ""),
                    col_data.get("units", ""),
                )
        console.print(col_table)
