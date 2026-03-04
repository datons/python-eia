"""Built-in data catalog and recipes for the EIA API v2.

The EIA API is a tree of routes. This module provides:
- Curated route metadata with descriptions and key facets
- Named "recipes" — pre-configured queries for common use cases
- Facet cheat-sheets so users don't have to discover facet values every time
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DataColumn:
    """Metadata for a data column from the API schema."""

    id: str
    units: str = ""
    aggregation_method: str = ""
    alias: str = ""


@dataclass(frozen=True)
class Frequency:
    """Metadata for a frequency option from the API schema."""

    id: str
    description: str = ""
    query: str = ""
    format: str = ""


@dataclass(frozen=True)
class FacetHint:
    """Documents a facet's key values without requiring an API call."""

    id: str
    description: str
    common_values: dict[str, str]  # hand-curated subset (value_id → human label)
    values: dict[str, str] = field(default_factory=dict)  # full API values (value_id → name)


@dataclass(frozen=True)
class RouteInfo:
    """Curated metadata for a data route."""

    route: str
    name: str
    description: str
    frequency: str  # default frequency
    facets: tuple[FacetHint, ...]
    notes: str = ""
    # --- API-fetched schema (optional, populated by refresh) ---
    data_columns: tuple[DataColumn, ...] = ()
    frequencies: tuple[Frequency, ...] = ()
    start_period: str = ""
    end_period: str = ""
    default_date_format: str = ""
    api_hash: str = ""
    last_refreshed: str = ""


@dataclass(frozen=True)
class Recipe:
    """A named, pre-configured query for a common use case."""

    id: str
    name: str
    description: str
    route: str
    facets: dict[str, str | list[str]]
    frequency: str
    notes: str = ""
    cli_example: str = ""
    python_example: str = ""


# ── Route & Recipe Catalog (loaded from YAML) ─────────────────────────

from eia.catalog_manager import EIACatalogManager as _EIACatalogManager

_mgr = _EIACatalogManager()

ROUTES: dict[str, RouteInfo] = {r.route: r for r in _mgr._load_routes()}
RECIPES: dict[str, Recipe] = {r.id: r for r in _mgr._load_recipes()}


# ── Convenience functions ──────────────────────────────────────────────

def get_route(route: str) -> RouteInfo:
    """Look up route metadata."""
    if route not in ROUTES:
        raise KeyError(
            f"Unknown route '{route}'. Use catalog.list_routes() to see available routes."
        )
    return ROUTES[route]


def get_recipe(recipe_id: str) -> Recipe:
    """Look up a named recipe."""
    if recipe_id not in RECIPES:
        raise KeyError(
            f"Unknown recipe '{recipe_id}'. Available: {', '.join(RECIPES.keys())}"
        )
    return RECIPES[recipe_id]


def list_routes() -> list[str]:
    """Return all cataloged route paths."""
    return sorted(ROUTES.keys())


def list_recipes() -> list[str]:
    """Return all recipe IDs."""
    return sorted(RECIPES.keys())


def summary() -> str:
    """Return a human-readable summary of the catalog."""
    lines = ["EIA Data Catalog", "=" * 50, ""]

    lines.append("Routes:")
    for route_path, info in sorted(ROUTES.items()):
        lines.append(f"  {route_path}")
        lines.append(f"    {info.name}: {info.description}")
        lines.append(f"    Default frequency: {info.frequency}")
        if info.notes:
            lines.append(f"    Note: {info.notes}")

    lines.append("")
    lines.append("Recipes (pre-configured queries):")
    for recipe_id, recipe in sorted(RECIPES.items()):
        lines.append(f"  {recipe_id}: {recipe.name}")
        lines.append(f"    {recipe.description}")

    return "\n".join(lines)
