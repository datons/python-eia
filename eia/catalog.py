"""Built-in data catalog and recipes for the EIA API v2.

The EIA API is a tree of routes. This module provides:
- Curated route metadata with descriptions and key facets
- Named "recipes" — pre-configured queries for common use cases
- Facet cheat-sheets so users don't have to discover facet values every time
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FacetHint:
    """Documents a facet's key values without requiring an API call."""

    id: str
    description: str
    common_values: dict[str, str]  # value_id → human label


@dataclass(frozen=True)
class RouteInfo:
    """Curated metadata for a data route."""

    route: str
    name: str
    description: str
    frequency: str  # default frequency
    facets: tuple[FacetHint, ...]
    notes: str = ""


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


# ── Route Catalog ──────────────────────────────────────────────────────

ROUTES: dict[str, RouteInfo] = {
    # Electricity
    "electricity/rto/fuel-type-data": RouteInfo(
        route="electricity/rto/fuel-type-data",
        name="Real-Time Grid Generation by Fuel Type",
        description="Hourly generation data by fuel type for US grid operators (RTO/BA)",
        frequency="hourly",
        facets=(
            FacetHint("respondent", "Grid operator (RTO/BA)", {
                "CISO": "CAISO (California)",
                "PJM": "PJM Interconnection",
                "MISO": "MISO",
                "ERCO": "ERCOT (Texas)",
                "ISNE": "ISO New England",
                "NYIS": "NYISO",
                "SWPP": "SPP",
                "US48": "Lower 48 Total",
            }),
            FacetHint("fueltype", "Generation fuel type", {
                "SUN": "Solar",
                "WND": "Wind",
                "NG": "Natural Gas",
                "NUC": "Nuclear",
                "COL": "Coal",
                "WAT": "Hydro",
                "OIL": "Petroleum",
                "OTH": "Other",
                "ALL": "All Fuels",
            }),
        ),
    ),
    "electricity/rto/region-data": RouteInfo(
        route="electricity/rto/region-data",
        name="Real-Time Grid Demand/Generation by Region",
        description="Hourly demand, generation, and net generation by US grid operator",
        frequency="hourly",
        facets=(
            FacetHint("respondent", "Grid operator (RTO/BA)", {
                "US48": "Lower 48 Total", "CISO": "CAISO", "PJM": "PJM",
                "MISO": "MISO", "ERCO": "ERCOT", "ISNE": "ISO-NE",
            }),
            FacetHint("type", "Data type", {
                "D": "Demand", "NG": "Net Generation", "TI": "Total Interchange",
            }),
        ),
    ),
    "electricity/rto/interchange-data": RouteInfo(
        route="electricity/rto/interchange-data",
        name="Real-Time Interchange Between Regions",
        description="Hourly power interchange between US grid operators",
        frequency="hourly",
        facets=(
            FacetHint("fromba", "Exporting BA", {"CISO": "CAISO", "PJM": "PJM", "MISO": "MISO"}),
            FacetHint("toba", "Importing BA", {"CISO": "CAISO", "PJM": "PJM", "MISO": "MISO"}),
        ),
    ),
    "electricity/retail-sales": RouteInfo(
        route="electricity/retail-sales",
        name="Retail Electricity Sales",
        description="Monthly/annual retail electricity sales, revenue, customers, and prices by state and sector",
        frequency="monthly",
        facets=(
            FacetHint("stateid", "US State", {"CA": "California", "TX": "Texas", "NY": "New York", "US": "US Total"}),
            FacetHint("sectorid", "Customer sector", {
                "RES": "Residential", "COM": "Commercial", "IND": "Industrial",
                "TRA": "Transportation", "ALL": "All Sectors",
            }),
        ),
    ),

    # Petroleum
    "petroleum/pri/spt": RouteInfo(
        route="petroleum/pri/spt",
        name="Spot Petroleum Prices",
        description="Daily/weekly spot prices for crude oil, gasoline, heating oil, and other products",
        frequency="daily",
        facets=(
            FacetHint("series", "Price series", {
                "RWTC": "WTI Crude Oil (Cushing)",
                "RBRTE": "Brent Crude Oil",
                "EMM_EPMRU_PTE_NUS_DPG": "Regular Gasoline (US avg)",
            }),
        ),
    ),

    # Natural Gas
    "natural-gas/pri/sum": RouteInfo(
        route="natural-gas/pri/sum",
        name="Natural Gas Prices Summary",
        description="Natural gas prices by type (wellhead, city gate, residential, etc.)",
        frequency="monthly",
        facets=(
            FacetHint("duoarea", "Area", {"NUS": "US Total"}),
            FacetHint("process", "Price type", {
                "PRS": "Residential", "PCS": "Commercial", "PIN": "Industrial",
                "PEU": "Electric Power", "PG1": "City Gate",
            }),
        ),
    ),
    "natural-gas/move/expc": RouteInfo(
        route="natural-gas/move/expc",
        name="US Natural Gas Exports by Country",
        description="Monthly US natural gas exports (pipeline and LNG) by destination country",
        frequency="monthly",
        facets=(
            FacetHint("process", "Export type", {
                "ENG": "LNG Exports (US total only)",
                "EVE": "Exports by Vessel (per country — LNG volumes & prices)",
                "ETR": "Exports by Truck",
                "ENP": "Pipeline Exports",
                "EEX": "Total Exports",
                "ERE": "Re-Exports",
            }),
            FacetHint("duoarea", "Destination (NUS-Nxx format)", {
                "NUS-Z00": "US Total",
                "NUS-NUK": "UK (GBR)", "NUS-NFR": "France", "NUS-NSP": "Spain",
                "NUS-NNL": "Netherlands", "NUS-NIT": "Italy", "NUS-NGM": "Germany",
                "NUS-NPO": "Portugal", "NUS-NGR": "Greece", "NUS-NTU": "Turkey",
                "NUS-NPL": "Poland", "NUS-NLH": "Lithuania", "NUS-NHR": "Croatia",
                "NUS-NFI": "Finland",
                "NUS-NJA": "Japan", "NUS-NKS": "South Korea", "NUS-NCH": "China",
                "NUS-NIN": "India", "NUS-NBR": "Brazil", "NUS-NMX": "Mexico",
            }),
            FacetHint("series", "Series type suffix", {
                "_MMCF": "Volume (Million Cubic Feet)",
                "_DMCF": "Price (Dollars per Thousand Cubic Feet)",
            }),
        ),
        notes=(
            "IMPORTANT: For per-country LNG volumes, use process=EVE (Exports by Vessel), "
            "NOT process=ENG (which only returns the US aggregate). "
            "Each country has two series: _MMCF (volume) and _DMCF (price). "
            "Filter with series.str.contains('MMCF') for volumes."
        ),
    ),
    "natural-gas/move/impc": RouteInfo(
        route="natural-gas/move/impc",
        name="US Natural Gas Imports by Country",
        description="Monthly US natural gas imports (pipeline and LNG) by origin country",
        frequency="monthly",
        facets=(
            FacetHint("process", "Import type", {
                "ING": "LNG Imports", "INP": "Pipeline Imports", "IRP": "Total Imports",
            }),
            FacetHint("duoarea", "Origin country", {}),
        ),
    ),

    # Total Energy
    "total-energy/data": RouteInfo(
        route="total-energy/data",
        name="Total Energy Overview",
        description="Monthly/annual total energy production, consumption, imports, exports, and prices",
        frequency="monthly",
        facets=(
            FacetHint("msn", "Series code (Monthly Series Number)", {}),
        ),
        notes="Very large dataset. Filter by msn facet for specific series.",
    ),
}


# ── Recipes (pre-configured queries) ──────────────────────────────────

RECIPES: dict[str, Recipe] = {
    "lng-exports-europe": Recipe(
        id="lng-exports-europe",
        name="US LNG Exports to Europe",
        description="Monthly LNG export volumes by vessel to European countries",
        route="natural-gas/move/expc",
        facets={"process": "EVE"},
        frequency="monthly",
        notes=(
            "Returns ALL countries. Filter df for European duoarea codes "
            "(NUS-NUK, NUS-NFR, NUS-NSP, NUS-NNL, NUS-NIT, NUS-NGM, etc.) "
            "and series containing 'MMCF' for volumes."
        ),
        cli_example=(
            "eia get natural-gas/move/expc --facet process=EVE --start 2024-01 --end 2025-12\n"
            "  # Then filter output for European countries and MMCF series"
        ),
        python_example=(
            "data = client.get_data_endpoint('natural-gas/move/expc')\n"
            "df = data.get(facets={'process': 'EVE'}, frequency='monthly', start='2024-01', end='2025-12')\n"
            "europe = ['NUS-NFR','NUS-NGM','NUS-NUK','NUS-NNL','NUS-NSP','NUS-NIT']\n"
            "vol = df[df['series'].str.contains('MMCF') & df['duoarea'].isin(europe)]"
        ),
    ),
    "lng-exports-asia": Recipe(
        id="lng-exports-asia",
        name="US LNG Exports to Asia",
        description="Monthly LNG export volumes by vessel to Asian countries",
        route="natural-gas/move/expc",
        facets={"process": "EVE"},
        frequency="monthly",
        notes=(
            "Filter for: NUS-NJA (Japan), NUS-NKS (South Korea), NUS-NCH (China), "
            "NUS-NIN (India), NUS-NTW (Taiwan)"
        ),
        python_example=(
            "data = client.get_data_endpoint('natural-gas/move/expc')\n"
            "df = data.get(facets={'process': 'EVE'}, frequency='monthly', start='2024-01', end='2025-12')\n"
            "asia = ['NUS-NJA','NUS-NKS','NUS-NCH','NUS-NIN','NUS-NTW']\n"
            "vol = df[df['series'].str.contains('MMCF') & df['duoarea'].isin(asia)]"
        ),
    ),
    "us-grid-solar-wind": Recipe(
        id="us-grid-solar-wind",
        name="US Grid Solar & Wind Generation",
        description="Hourly solar and wind generation for the Lower 48",
        route="electricity/rto/fuel-type-data",
        facets={"respondent": "US48", "fueltype": ["SUN", "WND"]},
        frequency="hourly",
        cli_example=(
            "eia get electricity/rto/fuel-type-data "
            "--facet respondent=US48 --facet fueltype=SUN --facet fueltype=WND "
            "--start 2024-06-01 --end 2024-06-08 --frequency hourly --data value"
        ),
        python_example=(
            "data = client.get_data_endpoint('electricity/rto/fuel-type-data')\n"
            "df = data.get(\n"
            "    facets={'respondent': 'US48', 'fueltype': ['SUN', 'WND']},\n"
            "    frequency='hourly', start='2024-06-01', end='2024-06-08',\n"
            "    data_columns=['value'],\n"
            ")"
        ),
    ),
    "crude-oil-prices": Recipe(
        id="crude-oil-prices",
        name="WTI & Brent Crude Oil Prices",
        description="Daily spot prices for WTI and Brent crude oil",
        route="petroleum/pri/spt",
        facets={"series": ["RWTC", "RBRTE"]},
        frequency="daily",
        cli_example=(
            "eia get petroleum/pri/spt --facet series=RWTC --facet series=RBRTE "
            "--start 2024-01-01 --end 2024-12-31"
        ),
        python_example=(
            "data = client.get_data_endpoint('petroleum/pri/spt')\n"
            "df = data.get(\n"
            "    facets={'series': ['RWTC', 'RBRTE']},\n"
            "    frequency='daily', start='2024-01-01', end='2024-12-31',\n"
            ")"
        ),
    ),
    "retail-electricity-prices": Recipe(
        id="retail-electricity-prices",
        name="Retail Electricity Prices by State",
        description="Monthly average retail electricity prices by state and sector",
        route="electricity/retail-sales",
        facets={"sectorid": "ALL"},
        frequency="monthly",
        cli_example=(
            "eia get electricity/retail-sales --facet stateid=CA --facet sectorid=ALL "
            "--start 2024-01 --end 2024-12 --data price"
        ),
        python_example=(
            "data = client.get_data_endpoint('electricity/retail-sales')\n"
            "df = data.get(\n"
            "    facets={'stateid': 'CA', 'sectorid': 'ALL'},\n"
            "    data_columns=['price'], frequency='monthly',\n"
            "    start='2024-01', end='2024-12',\n"
            ")"
        ),
    ),
}


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
