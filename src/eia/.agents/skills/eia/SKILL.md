---
name: eia
description: Query U.S. energy data (EIA API v2). Use when the user asks about U.S. electricity, petroleum, natural gas, or coal data from the EIA.
version: 2.0.0
---

# EIA Data Assistant

You have access to the `python-eia` library and CLI for querying the U.S. Energy Information Administration (EIA) API v2.

## When to use what

- **Python scripts** (default): reproducible, composable, saveable. Use for any data work the user will want to keep or iterate on.
- **CLI**: quick one-shot lookups, exploration, sanity checks. Use when the user wants a fast answer they won't need again.
- **If unsure**: ask the user whether they want a script or a quick CLI check.

## Built-in Catalog (OFFLINE — no API calls)

The library ships with a YAML catalog containing full API schema for curated routes: columns, frequencies, periods, and **all facet values**. Always check the catalog first to avoid unnecessary API calls.

### Cataloged Routes

| Route | Description | Frequency |
|-------|-------------|-----------|
| `electricity/rto/fuel-type-data` | Real-time grid generation by fuel type | hourly |
| `electricity/rto/region-data` | Real-time grid demand/generation by region | hourly |
| `electricity/rto/interchange-data` | Real-time interchange between regions | hourly |
| `electricity/retail-sales` | Retail electricity sales by state/sector | monthly |
| `petroleum/pri/spt` | Spot petroleum prices (crude, gasoline, etc.) | daily |
| `natural-gas/pri/sum` | Natural gas prices summary | monthly |
| `natural-gas/move/expc` | US natural gas exports by country | monthly |
| `natural-gas/move/impc` | US natural gas imports by country | monthly |
| `total-energy/data` | Total energy overview (production, consumption, etc.) | monthly |

For routes **not** in the catalog, use `eia routes` (CLI) to discover and `eia meta` to inspect.

## Python Library (default)

```python
from eia import EIAClient

client = EIAClient()  # reads config file, then EIA_API_KEY env var

# --- Catalog access (offline, no API calls) ---

# Get endpoint with cached schema — no API metadata call
data = client.get_data_endpoint("electricity/rto/fuel-type-data")

# Inspect metadata (all cached for cataloged routes)
data.facets                    # FacetContainer with attribute access
data.frequencies               # List[FrequencyInfo]
data.data_columns              # Dict[str, DataColumnInfo]
data.start_period              # "2019-01-01T00"
data.end_period                # "2026-03-04T07"

# Facet values — cached, no API call
respondents = data.facets.respondent.get_values()
# [FacetValue(id='CISO', name='California ISO'), ...]

fuel_types = data.facets.fueltype.get_values()
# [FacetValue(id='SUN', name='Solar'), ...]

# Or access catalog directly
from eia.catalog import get_route, list_routes
route = get_route("electricity/rto/fuel-type-data")
route.data_columns   # (DataColumn(id='value', units='megawatthours', ...),)
route.frequencies     # (Frequency(id='hourly', ...), Frequency(id='local-hourly', ...))
route.facets[0].values  # {'CISO': 'California ISO', 'PJM': 'PJM Interconnection LLC', ...}

# --- Fetch data (hits API) ---

df = data.get(
    data_columns=["value"],
    facets={"respondent": "CISO"},
    frequency="hourly",
    start="2024-01-01",
    end="2024-01-31",
    sort=[{"column": "period", "direction": "desc"}],
)

# Multiple facet values
df = data.get(
    data_columns=["revenue", "sales"],
    facets={"stateid": "CA", "sectorid": ["RES", "COM"]},
    frequency="monthly",
    start="2024-01-01",
    end="2024-12-31",
)

# --- Route tree navigation (for discovery — hits API) ---
route = client.route("electricity/rto/fuel-type-data")
route.routes          # Dict of child routes (if branch node)
route.data            # Data object (if leaf node)
```

### Facet conventions

- **Common facets**: `respondent` (grid operator), `fueltype`, `stateid`, `sectorid`, `series`
- **Multiple values**: pass a list — `facets={"sectorid": ["RES", "COM"]}`
- **Prefer catalog** for facet discovery: `get_route().facets[i].values` has all valid values offline

### Key conventions

- The `period` column is auto-converted to datetime (UTC for non-local frequencies)
- The `value` column is auto-converted to numeric
- Pagination is automatic by default (fetches all pages)
- API page limit is 5000 rows per request
- Custom exception: `EIAError` (includes HTTP status code and API error code)

## CLI Reference (quick lookups)

### Catalog (offline)

```bash
eia catalog routes                              # List all cataloged routes
eia catalog show electricity/rto/fuel-type-data # Full details (columns, frequencies, facet values)
eia catalog recipes                             # Pre-configured query recipes
eia catalog recipe lng-exports-europe           # Show a specific recipe
eia catalog refresh --apply                     # Refresh schema from API
```

### Explore (hits API)

```bash
eia routes                                      # Top-level routes
eia routes electricity/rto                      # Navigate deeper
eia meta electricity/rto/fuel-type-data         # Endpoint metadata
eia facets electricity/rto/fuel-type-data respondent  # Facet values
```

### Fetch data

```bash
eia get electricity/rto/fuel-type-data \
  --start 2024-06-01 --end 2024-06-08 \
  --frequency hourly --facet respondent=CISO --data value

# Multiple facet values (repeat --facet)
eia get electricity/retail-sales \
  --start 2024-01-01 --end 2024-12-31 \
  --facet stateid=CA --facet sectorid=RES --facet sectorid=COM \
  --data revenue --data sales

# Export
eia get petroleum/pri/spt --start 2024-01-01 --end 2024-06-01 \
  --format csv --output prices.csv
```

### Exec (ad-hoc pandas)

```bash
eia exec electricity/rto/fuel-type-data \
  --start 2024-06-01 --end 2024-06-08 \
  --frequency hourly --facet respondent=CISO --data value \
  -x "df.groupby('fueltype')['value'].mean()"
```

### Output options

```
--format table|csv|json   (default: table)
--output file.csv         (write to file instead of stdout)
```

## Configuration

```bash
eia config set api-key YOUR_KEY    # Store API key
eia config get api-key             # Verify
```

Config file: `~/.config/eia/config.toml`. API key resolution: config file > `EIA_API_KEY` env var.
