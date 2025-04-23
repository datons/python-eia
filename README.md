# Python EIA Client

A Python client for interacting with the U.S. Energy Information Administration (EIA) API v2.

## Installation

You can install the package directly from PyPI:

```bash
pip install python-eia
```

For development installation with extra tools:

```bash
pip install python-eia[dev]
```

## Usage

```python
from eia.client import EIAClient

# Initialize the client with your API key
client = EIAClient('your-api-key')

# Get data for a specific series
series_data = client.get_series('ELEC.GEN.ALL-AL-99.A')

# Search for series
search_results = client.search('electricity generation')

# Get category information
categories = client.get_categories()
category_info = client.get_category('371')

# Get geographical sets
geosets = client.get_geosets()
geoset_info = client.get_geoset('USA')

# Don't forget to close the client when you're done
client.close()
```

## Features

- Retrieve time series data by series ID
- Search for series using keywords
- Get category information and metadata
- Access geographical datasets
- Automatic error handling and retries
- Configurable request timeout
- Type hints for better IDE support

## Error Handling

The client includes built-in error handling for common API issues:

- `InvalidAPIKeyError`: Raised when the API key is invalid or missing
- `RateLimitError`: Raised when API rate limits are exceeded
- `InvalidSeriesError`: Raised when requesting an invalid series ID
- `APIError`: Base class for API-related errors

## Requirements

- Python 3.7+
- requests>=2.31.0
- urllib3>=2.0.0

## Development

To set up the development environment:

```bash
pip install -e ".[dev]"
```

## License

MIT License 