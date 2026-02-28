"""CLI commands for cache management."""

from __future__ import annotations

from typing import Optional

import typer

cache_app = typer.Typer(help="Manage the local parquet cache.")


@cache_app.command(name="status")
def cache_status():
    """Show cache statistics (files, size, routes)."""
    from eia.cache import CacheConfig, CacheStore

    store = CacheStore(CacheConfig())
    info = store.status()

    typer.echo(f"Cache path: {info['path']}")
    typer.echo(f"Files:      {info['files']}")
    typer.echo(f"Size:       {info['size_mb']} MB")

    routes = info.get("routes", {})
    if routes:
        typer.echo("\nRoutes:")
        for route, count in sorted(routes.items()):
            typer.echo(f"  {route}: {count} files")


@cache_app.command(name="path")
def cache_path():
    """Print the cache directory path."""
    from eia.cache import CacheConfig

    typer.echo(str(CacheConfig().cache_dir))


@cache_app.command(name="clear")
def cache_clear(
    route: Optional[str] = typer.Option(None, "--route", "-r", help="Route to clear (e.g. electricity/rto/fuel-type-data)"),
    frequency: Optional[str] = typer.Option(None, "--frequency", "-f", help="Frequency to clear (e.g. hourly)"),
):
    """Clear cached data.

    Without flags, clears the entire cache. Use --route and/or --frequency
    to target specific partitions.
    """
    from eia.cache import CacheConfig, CacheStore

    store = CacheStore(CacheConfig())
    removed = store.clear(route=route, frequency=frequency)
    typer.echo(f"Removed {removed} cached file(s).")
