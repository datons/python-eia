---
name: eia
description: Query U.S. energy data (EIA API v2). Use when the user asks about U.S. electricity, petroleum, natural gas, or coal data from the EIA.
version: 1.0.0
---

# EIA Data Assistant

You have access to the `python-eia` CLI and library for querying the U.S. Energy Information Administration (EIA) API v2.

The EIA API is a **route-based tree**. You navigate routes to find data endpoints, then query them with facet filters and frequency options.

## CLI Reference

### Explore the API tree

```bash
# Top-level routes
eia routes

# Navigate deeper
eia routes electricity
eia routes electricity/rto
eia routes electricity/rto/fuel-type-data  # Error if leaf — use 'eia meta' instead
```

### Inspect a data endpoint

```bash
# Show facets, frequencies, and data columns
eia meta electricity/rto/fuel-type-data
eia meta petroleum/pri/spt
eia meta natural-gas/pri/sum
```

### List facet values

```bash
# List all values for a facet
eia facets electricity/rto/fuel-type-data respondent
eia facets electricity/rto/fuel-type-data fueltype
eia facets petroleum/pri/spt series --format csv
```

### Fetch data

```bash
# Basic query
eia get electricity/rto/fuel-type-data \
  --start 2024-06-01 --end 2024-06-08 \
  --frequency hourly \
  --facet respondent=CISO \
  --data value

# Multiple facet values (repeat --facet)
eia get electricity/retail-sales \
  --start 2024-01-01 --end 2024-12-31 \
  --facet stateid=CA --facet sectorid=RES --facet sectorid=COM \
  --data revenue --data sales

# Export to CSV
eia get petroleum/pri/spt --start 2024-01-01 --end 2024-06-01 \
  --format csv --output prices.csv

# Sort
eia get electricity/rto/fuel-type-data \
  --start 2024-06-01 --end 2024-06-02 \
  --frequency hourly --facet respondent=CISO --data value \
  --sort period --sort-dir desc
```

### Fetch + eval pandas expression

```bash
# Descriptive stats
eia exec electricity/rto/fuel-type-data \
  --start 2024-06-01 --end 2024-06-08 \
  --frequency hourly --facet respondent=CISO --data value \
  -x "df.describe()"

# Group by fuel type
eia exec electricity/rto/fuel-type-data \
  --start 2024-06-01 --end 2024-06-08 \
  --frequency hourly --facet respondent=CISO --data value \
  -x "df.groupby('fueltype')['value'].mean()"

# Daily aggregation
eia exec natural-gas/pri/sum \
  --start 2024-01-01 --end 2024-06-01 \
  -x "df.groupby('process')['value'].mean().sort_values(ascending=False)"
```

### Output options (all commands)

```
--format table|csv|json   (default: table)
--output file.csv         (write to file instead of stdout)
```

## Common Routes

| Route | Description |
|-------|-------------|
| `electricity/rto/fuel-type-data` | Real-time grid generation by fuel type |
| `electricity/rto/region-data` | Real-time grid demand/generation by region |
| `electricity/rto/interchange-data` | Real-time interchange between regions |
| `electricity/retail-sales` | Retail electricity sales (monthly/annual) |
| `electricity/electric-power-operational-data` | Power plant operational data |
| `petroleum/pri/spt` | Spot petroleum prices (crude, gasoline, etc.) |
| `petroleum/sum/sndw` | Weekly petroleum supply/demand |
| `natural-gas/pri/sum` | Natural gas prices summary |
| `natural-gas/sum/lsum` | Natural gas supply/demand summary |
| `coal/shipments/receipts` | Coal shipments and receipts |
| `total-energy/data` | Total energy overview (monthly/annual) |

Use `eia routes` to discover more. Use `eia meta <route>` to see exact facets and frequencies.

## Facet Conventions

- **Format**: `--facet key=value` (repeatable)
- **Multiple values**: repeat the flag — `--facet sectorid=RES --facet sectorid=COM`
- **Common facets**: `respondent` (grid operator), `fueltype`, `stateid`, `sectorid`, `series`
- Each endpoint has different facets — use `eia meta` and `eia facets` to discover them

## Python Library

```python
from eia import EIAClient

client = EIAClient()  # reads config file, then EIA_API_KEY env var

# Navigate the route tree
route = client.route("electricity/rto/fuel-type-data")
route.routes          # Dict of child routes (if branch node)
route.data            # Data object (if leaf node)

# Inspect metadata
route.data.facets              # FacetContainer with attribute access
route.data.frequencies         # List[FrequencyInfo]
route.data.data_columns        # Dict[str, DataColumnInfo]
route.data.facets.respondent.get_values()  # List[FacetValue]

# Direct access to a data endpoint
data = client.get_data_endpoint("electricity/rto/fuel-type-data")

# Fetch data as DataFrame
df = data.get(
    data_columns=["value"],
    facets={"respondent": "CISO"},
    frequency="hourly",
    start="2024-01-01",
    end="2024-01-31",
    sort=[{"column": "period", "direction": "desc"}],
)
```

## Configuration

```bash
# Store your API key persistently (recommended)
eia config set api-key YOUR_KEY

# Verify it's stored
eia config get api-key
```

The config file is stored at `~/.config/eia/config.toml`.

## Key Conventions

- The `period` column is auto-converted to datetime (UTC for non-local frequencies)
- The `value` column is auto-converted to numeric
- Pagination is automatic by default (fetches all pages)
- API key resolution: config file (`~/.config/eia/config.toml`) > `EIA_API_KEY` env var
- API page limit is 5000 rows per request
- Custom exception: `EIAError` (includes HTTP status code and API error code)
