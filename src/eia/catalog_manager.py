"""YAML-backed catalog manager for EIA routes and recipes.

Loads curated route metadata and recipes from YAML files shipped with
the package, exposing them as dataclass instances and DataFrames.
"""

from __future__ import annotations

import hashlib
import importlib.resources
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import pandas as pd
import yaml

from eia.catalog import DataColumn, FacetHint, Frequency, Recipe, RouteInfo

if TYPE_CHECKING:
    from eia.client import EIAClient

logger = logging.getLogger(__name__)


@dataclass
class RefreshResult:
    """Result of a catalog refresh operation."""

    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class EIACatalogManager:
    """Manages the YAML-backed EIA data catalog.

    Parameters
    ----------
    client : EIAClient, optional
        An EIA client instance, needed only for ``refresh()``.
    """

    def __init__(self, client: Optional[EIAClient] = None) -> None:
        self._client = client
        self._routes: list[RouteInfo] | None = None
        self._recipes: list[Recipe] | None = None

    # ── YAML loading ──────────────────────────────────────────────────

    @staticmethod
    def _read_yaml(filename: str) -> dict:
        """Read a YAML file from the ``eia.data`` package."""
        ref = importlib.resources.files("eia.data").joinpath(filename)
        with importlib.resources.as_file(ref) as path:
            return yaml.safe_load(path.read_text(encoding="utf-8"))

    def _load_routes(self) -> list[RouteInfo]:
        """Parse ``routes.yaml`` into a list of :class:`RouteInfo`."""
        if self._routes is not None:
            return self._routes

        data = self._read_yaml("routes.yaml")
        routes: list[RouteInfo] = []
        for entry in data.get("routes", []):
            facets = tuple(
                FacetHint(
                    id=f["id"],
                    description=f.get("description", ""),
                    common_values=f.get("common_values") or {},
                    values=f.get("values") or {},
                )
                for f in entry.get("facets", [])
            )
            data_columns = tuple(
                DataColumn(
                    id=c["id"],
                    units=c.get("units", ""),
                    aggregation_method=c.get("aggregation_method", ""),
                    alias=c.get("alias", ""),
                )
                for c in entry.get("data_columns", [])
            )
            frequencies = tuple(
                Frequency(
                    id=f["id"],
                    description=f.get("description", ""),
                    query=f.get("query", ""),
                    format=f.get("format", ""),
                )
                for f in entry.get("frequencies", [])
            )
            routes.append(
                RouteInfo(
                    route=entry["route"],
                    name=entry["name"],
                    description=entry.get("description", ""),
                    frequency=entry.get("frequency", ""),
                    facets=facets,
                    notes=entry.get("notes") or "",
                    data_columns=data_columns,
                    frequencies=frequencies,
                    start_period=entry.get("start_period", ""),
                    end_period=entry.get("end_period", ""),
                    default_date_format=entry.get("default_date_format", ""),
                    api_hash=entry.get("api_hash", ""),
                    last_refreshed=entry.get("last_refreshed", ""),
                )
            )
        self._routes = routes
        return routes

    def _load_recipes(self) -> list[Recipe]:
        """Parse ``recipes.yaml`` into a list of :class:`Recipe`."""
        if self._recipes is not None:
            return self._recipes

        data = self._read_yaml("recipes.yaml")
        recipes: list[Recipe] = []
        for entry in data.get("recipes", []):
            facets: dict[str, str | list[str]] = {}
            for k, v in (entry.get("facets") or {}).items():
                facets[k] = v

            recipes.append(
                Recipe(
                    id=entry["id"],
                    name=entry["name"],
                    description=entry.get("description", ""),
                    route=entry["route"],
                    facets=facets,
                    frequency=entry.get("frequency", ""),
                    notes=entry.get("notes") or "",
                    cli_example=entry.get("cli_example") or "",
                    python_example=entry.get("python_example") or "",
                )
            )
        self._recipes = recipes
        return recipes

    # ── Public API ────────────────────────────────────────────────────

    def list_routes(self, query: str | None = None) -> pd.DataFrame:
        """Return a DataFrame of all cataloged routes.

        Parameters
        ----------
        query : str, optional
            Case-insensitive filter applied to route, name, and description.
        """
        routes = self._load_routes()
        rows = [
            {"route": r.route, "name": r.name, "description": r.description, "frequency": r.frequency}
            for r in routes
        ]
        df = pd.DataFrame(rows)
        if query and not df.empty:
            q = query.lower()
            mask = (
                df["route"].str.lower().str.contains(q, na=False)
                | df["name"].str.lower().str.contains(q, na=False)
                | df["description"].str.lower().str.contains(q, na=False)
            )
            df = df[mask]
        return df

    def list_recipes(self, query: str | None = None) -> pd.DataFrame:
        """Return a DataFrame of all cataloged recipes.

        Parameters
        ----------
        query : str, optional
            Case-insensitive filter applied to id, name, and description.
        """
        recipes = self._load_recipes()
        rows = [
            {"id": r.id, "name": r.name, "description": r.description, "route": r.route, "frequency": r.frequency}
            for r in recipes
        ]
        df = pd.DataFrame(rows)
        if query and not df.empty:
            q = query.lower()
            mask = (
                df["id"].str.lower().str.contains(q, na=False)
                | df["name"].str.lower().str.contains(q, na=False)
                | df["description"].str.lower().str.contains(q, na=False)
            )
            df = df[mask]
        return df

    def get_route(self, route: str) -> RouteInfo:
        """Look up a single route by path.

        Raises
        ------
        KeyError
            If the route is not in the catalog.
        """
        for r in self._load_routes():
            if r.route == route:
                return r
        raise KeyError(
            f"Unknown route '{route}'. Use catalog.list_routes() to see available routes."
        )

    def get_recipe(self, recipe_id: str) -> Recipe:
        """Look up a single recipe by ID.

        Raises
        ------
        KeyError
            If the recipe ID is not in the catalog.
        """
        for r in self._load_recipes():
            if r.id == recipe_id:
                return r
        available = ", ".join(r.id for r in self._load_recipes())
        raise KeyError(f"Unknown recipe '{recipe_id}'. Available: {available}")

    @staticmethod
    def _routes_yaml_path() -> Path:
        """Return the filesystem path to ``routes.yaml``."""
        ref = importlib.resources.files("eia.data").joinpath("routes.yaml")
        # as_file returns the real path for editable installs
        with importlib.resources.as_file(ref) as p:
            return Path(p)

    @staticmethod
    def _compute_api_hash(api_meta: dict[str, Any]) -> str:
        """SHA-256 of the API metadata response (deterministic)."""
        return hashlib.sha256(
            json.dumps(api_meta, sort_keys=True).encode()
        ).hexdigest()

    @staticmethod
    def _extract_schema_from_api(
        api_meta: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract schema fields from an API metadata response.

        Returns a dict with keys matching RouteInfo API-fetched fields.
        """
        data_columns = []
        for col_id, col_data in (api_meta.get("data", {}) or {}).items():
            if isinstance(col_data, dict):
                data_columns.append({
                    "id": col_id,
                    "units": col_data.get("units", ""),
                    "aggregation_method": col_data.get("aggregation-method", ""),
                    "alias": col_data.get("alias", ""),
                })

        frequencies = []
        for freq in api_meta.get("frequency", []):
            if isinstance(freq, dict) and "id" in freq:
                frequencies.append({
                    "id": freq["id"],
                    "description": freq.get("description", ""),
                    "query": freq.get("query", ""),
                    "format": freq.get("format", ""),
                })

        facets = []
        for facet in api_meta.get("facets", []):
            if isinstance(facet, dict) and "id" in facet:
                facets.append({
                    "id": facet["id"],
                    "description": facet.get("description", ""),
                })

        return {
            "name": api_meta.get("name", ""),
            "description": api_meta.get("description", ""),
            "default_frequency": api_meta.get("defaultFrequency", ""),
            "start_period": api_meta.get("startPeriod", ""),
            "end_period": api_meta.get("endPeriod", ""),
            "default_date_format": api_meta.get("defaultDateFormat", ""),
            "data_columns": data_columns,
            "frequencies": frequencies,
            "facets": facets,
        }

    @staticmethod
    def _merge_route_entry(
        existing: dict[str, Any],
        schema: dict[str, Any],
        api_hash: str,
        facet_values: dict[str, dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Merge API-fetched schema into an existing YAML route entry.

        Preserves hand-curated fields: ``notes``, facets' ``common_values``.
        Overwrites facets' ``values`` with full API-fetched values.
        """
        merged = dict(existing)

        # Overwrite API-fetched scalar fields
        for key in ("name", "description", "start_period", "end_period",
                     "default_date_format", "data_columns"):
            merged[key] = schema[key]

        merged["frequency"] = schema.get("default_frequency", existing.get("frequency", ""))
        merged["frequencies"] = schema["frequencies"]
        merged["api_hash"] = api_hash
        merged["last_refreshed"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

        # Merge facets: API IDs + descriptions overwritten, common_values preserved,
        # values overwritten with full API-fetched values
        existing_facets_by_id: dict[str, dict] = {
            f["id"]: f for f in existing.get("facets", [])
        }
        facet_values = facet_values or {}
        merged_facets = []
        for api_facet in schema["facets"]:
            fid = api_facet["id"]
            old = existing_facets_by_id.get(fid, {})
            merged_facet: dict[str, Any] = {
                "id": fid,
                "description": api_facet["description"],
            }
            # Preserve hand-curated common_values
            if old.get("common_values"):
                merged_facet["common_values"] = old["common_values"]
            # Store full API-fetched values
            if fid in facet_values:
                merged_facet["values"] = facet_values[fid]
            merged_facets.append(merged_facet)
        merged["facets"] = merged_facets

        return merged

    def _save_yaml(self, route_entries: list[dict[str, Any]]) -> None:
        """Write route entries back to ``routes.yaml``."""
        path = self._routes_yaml_path()
        data = {"version": 1, "routes": route_entries}
        path.write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        # Invalidate cached routes
        self._routes = None

    def _fetch_route_data(
        self, route_path: str,
    ) -> tuple[dict[str, Any], dict[str, dict[str, str]], list[str]]:
        """Fetch metadata and all facet values for a single route.

        Returns (api_meta, facet_values, errors).
        """
        errors: list[str] = []
        api_meta = self._client.get_metadata(route_path)

        # Collect facet IDs, then fetch values in parallel
        facet_ids = [
            f["id"] for f in api_meta.get("facets", [])
            if isinstance(f, dict) and "id" in f
        ]

        facet_values: dict[str, dict[str, str]] = {}

        def fetch_facet(fid: str) -> tuple[str, dict[str, str] | None, str | None]:
            try:
                fv_response = self._client.get_facet_values(route_path, fid)
                values = {
                    item["id"]: item.get("name", item.get("description", ""))
                    for item in fv_response.get("facets", [])
                    if isinstance(item, dict) and "id" in item
                }
                return fid, values, None
            except Exception as e:
                return fid, None, f"Error fetching facet {fid} for {route_path}: {e}"

        with ThreadPoolExecutor(max_workers=5) as pool:
            for fid, values, err in pool.map(fetch_facet, facet_ids):
                if err:
                    errors.append(err)
                elif values is not None:
                    facet_values[fid] = values

        return api_meta, facet_values, errors

    def refresh(self, dry_run: bool = False) -> RefreshResult:
        """Fetch full API schema for each cataloged route and persist to YAML.

        Fetches routes and facet values in parallel for speed.
        Preserves hand-curated fields (notes, common_values).

        Parameters
        ----------
        dry_run : bool
            If True, report what would change without modifying files.

        Returns
        -------
        RefreshResult
            Summary of added / updated / unchanged routes.
        """
        if self._client is None:
            raise RuntimeError(
                "Cannot refresh without an EIA client. "
                "Pass client= when constructing EIACatalogManager."
            )

        result = RefreshResult()

        # Load raw YAML entries (dicts, not dataclasses) for merging
        raw_data = self._read_yaml("routes.yaml")
        raw_entries: list[dict[str, Any]] = raw_data.get("routes", [])

        # Fetch all routes in parallel
        fetch_results: dict[str, tuple[dict, dict, list]] = {}

        def fetch_one(entry: dict[str, Any]) -> tuple[str, dict | None, dict | None, list[str]]:
            route_path = entry["route"]
            try:
                api_meta, facet_values, errors = self._fetch_route_data(route_path)
                return route_path, api_meta, facet_values, errors
            except Exception as e:
                return route_path, None, None, [f"Error fetching {route_path}: {e}"]

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(fetch_one, entry): entry for entry in raw_entries}
            for future in as_completed(futures):
                route_path, api_meta, facet_values, errors = future.result()
                fetch_results[route_path] = (api_meta, facet_values, errors)

        # Process results in original order
        updated_entries: list[dict[str, Any]] = []
        for entry in raw_entries:
            route_path = entry["route"]
            api_meta, facet_values, errors = fetch_results[route_path]
            result.errors.extend(errors)

            if api_meta is None:
                updated_entries.append(entry)
                continue

            hash_input = {"meta": api_meta, "facet_values": facet_values}
            new_hash = self._compute_api_hash(hash_input)

            if new_hash == entry.get("api_hash", ""):
                result.unchanged.append(route_path)
                updated_entries.append(entry)
                continue

            schema = self._extract_schema_from_api(api_meta)
            merged = self._merge_route_entry(entry, schema, new_hash, facet_values)
            result.updated.append(route_path)
            updated_entries.append(merged)

        if not dry_run and result.updated:
            self._save_yaml(updated_entries)
            logger.info(
                "Refresh updated %d routes in routes.yaml.",
                len(result.updated),
            )

        return result
