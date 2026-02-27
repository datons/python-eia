"""CLI command: explore API route tree."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def routes_command(
    route: Optional[str] = typer.Argument(None, help="Route path (e.g. 'electricity' or 'electricity/rto')"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, csv, json"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="EIA API key"),
):
    """Explore the EIA API route tree.

    \b
    Examples:
        eia routes                       # Top-level routes
        eia routes electricity           # Child routes of electricity
        eia routes electricity/rto       # Deeper navigation
    """
    from eia.cli.app import get_client

    client = get_client(api_key)

    slug = route or ""
    metadata = client.get_metadata(slug)

    routes_list = metadata.get("routes", [])
    if not routes_list:
        typer.echo(f"No child routes found at '{slug or '/'}'.")
        if "data" in metadata or "facets" in metadata:
            typer.echo("This is a data endpoint. Use 'eia meta' to inspect it.")
        raise typer.Exit(0)

    if format == "json":
        import json

        text = json.dumps(routes_list, indent=2)
        if output:
            from pathlib import Path
            Path(output).write_text(text)
            typer.echo(f"Written to {output}")
        else:
            typer.echo(text)
        return

    if format == "csv":
        lines = ["id,name,description"]
        for r in routes_list:
            desc = (r.get("description") or "").replace(",", ";")
            lines.append(f"{r['id']},{r.get('name', '')},{desc}")
        text = "\n".join(lines)
        if output:
            from pathlib import Path
            Path(output).write_text(text)
            typer.echo(f"Written to {output}")
        else:
            typer.echo(text)
        return

    # Rich table
    table = Table(title=f"Routes: {slug or '/'}")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Description")

    for r in routes_list:
        table.add_row(
            r["id"],
            r.get("name", ""),
            r.get("description", ""),
        )

    console.print(table)
