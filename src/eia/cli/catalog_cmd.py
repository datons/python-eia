"""CLI command: browse the built-in data catalog and recipes."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from eia.catalog import ROUTES, RECIPES

catalog_app = typer.Typer(no_args_is_help=True)
console = Console()


@catalog_app.command("refresh")
def catalog_refresh(
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Show what would change without modifying files"),
):
    """Discover new routes from the live EIA API and compare with the catalog."""
    from eia.cli.app import get_client
    from eia.catalog_manager import EIACatalogManager

    client = get_client()
    mgr = EIACatalogManager(client)
    result = mgr.refresh(dry_run=dry_run)

    if result.errors:
        for err in result.errors:
            console.print(f"[red]Error:[/red] {err}")

    if result.updated:
        console.print(f"\n[blue]Updated schema ({len(result.updated)}):[/blue]")
        for r in result.updated:
            console.print(f"  ~ {r}")

    if result.added:
        console.print(f"\n[green]New routes ({len(result.added)}):[/green]")
        for r in result.added:
            console.print(f"  + {r}")

    if result.removed:
        console.print(f"\n[yellow]Routes in catalog but not discovered ({len(result.removed)}):[/yellow]")
        for r in result.removed:
            console.print(f"  - {r}")

    if not result.updated and not result.added:
        console.print("[green]All routes up to date.[/green]")

    console.print(f"\n[dim]Unchanged: {len(result.unchanged)} routes[/dim]")


@catalog_app.command("routes")
def catalog_routes(
    query: Optional[str] = typer.Argument(None, help="Filter routes by keyword"),
):
    """List all cataloged data routes with descriptions."""
    table = Table(title="EIA Data Routes", show_header=True, padding=(0, 1))
    table.add_column("Route", style="cyan")
    table.add_column("Name")
    table.add_column("Frequency", style="green")

    for route_path, info in sorted(ROUTES.items()):
        if query:
            q = query.lower()
            if q not in route_path.lower() and q not in info.name.lower() and q not in info.description.lower():
                continue
        table.add_row(route_path, info.name, info.frequency)

    console.print(table)


@catalog_app.command("show")
def catalog_show(
    route: str = typer.Argument(..., help="Route path (e.g. natural-gas/move/expc)"),
):
    """Show detailed info for a specific route, including facets and hints."""
    from eia.catalog import get_route

    try:
        info = get_route(route)
    except KeyError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]{info.name}[/bold]")
    console.print(f"  Route: {info.route}")
    console.print(f"  {info.description}")
    console.print(f"  Default frequency: {info.frequency}")

    if info.notes:
        console.print(f"\n  [yellow]Note:[/yellow] {info.notes}")

    if info.start_period or info.end_period:
        console.print(f"\n  Period: {info.start_period} → {info.end_period}")
    if info.default_date_format:
        console.print(f"  Date format: {info.default_date_format}")
    if info.last_refreshed:
        console.print(f"  [dim]Last refreshed: {info.last_refreshed}[/dim]")

    if info.data_columns:
        console.print(f"\n  [bold]Data Columns:[/bold]")
        col_table = Table(show_header=True, padding=(0, 1))
        col_table.add_column("Column", style="green")
        col_table.add_column("Alias")
        col_table.add_column("Units")
        col_table.add_column("Aggregation")
        for col in info.data_columns:
            col_table.add_row(col.id, col.alias, col.units, col.aggregation_method)
        console.print(col_table)

    if info.frequencies:
        console.print(f"\n  [bold]Frequencies:[/bold]")
        freq_table = Table(show_header=True, padding=(0, 1))
        freq_table.add_column("ID", style="green")
        freq_table.add_column("Description")
        freq_table.add_column("Query")
        freq_table.add_column("Format")
        for freq in info.frequencies:
            freq_table.add_row(freq.id, freq.description, freq.query, freq.format)
        console.print(freq_table)

    for facet in info.facets:
        console.print(f"\n  [cyan]Facet: {facet.id}[/cyan] — {facet.description}")
        if facet.common_values:
            table = Table(show_header=True, padding=(0, 1))
            table.add_column("Value", style="green")
            table.add_column("Description")
            for val_id, val_desc in sorted(facet.common_values.items()):
                table.add_row(val_id, val_desc)
            console.print(table)

    console.print()


@catalog_app.command("recipes")
def catalog_recipes(
    query: Optional[str] = typer.Argument(None, help="Filter recipes by keyword"),
):
    """List pre-configured query recipes for common use cases."""
    table = Table(title="EIA Recipes", show_header=True, padding=(0, 1))
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Route", style="green")

    for recipe_id, recipe in sorted(RECIPES.items()):
        if query:
            q = query.lower()
            if q not in recipe_id.lower() and q not in recipe.name.lower() and q not in recipe.description.lower():
                continue
        table.add_row(recipe_id, recipe.name, recipe.route)

    console.print(table)


@catalog_app.command("recipe")
def catalog_recipe(
    recipe_id: str = typer.Argument(..., help="Recipe ID (e.g. lng-exports-europe)"),
):
    """Show detailed info for a specific recipe, including code examples."""
    from eia.catalog import get_recipe

    try:
        recipe = get_recipe(recipe_id)
    except KeyError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]{recipe.name}[/bold]")
    console.print(f"  {recipe.description}")
    console.print(f"  Route: {recipe.route}")
    console.print(f"  Frequency: {recipe.frequency}")
    console.print(f"  Facets: {recipe.facets}")

    if recipe.notes:
        console.print(f"\n  [yellow]Note:[/yellow] {recipe.notes}")

    if recipe.cli_example:
        console.print(Panel(recipe.cli_example, title="CLI Example", border_style="green"))

    if recipe.python_example:
        console.print(Panel(recipe.python_example, title="Python Example", border_style="blue"))

    console.print()
