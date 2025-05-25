# Python EIA Client

A minimalist Python client for the U.S. Energy Information Administration (EIA) API v2.

## Installation

```bash
pip install python-eia
```

## API Key

You must request an API key from the [EIA website](https://www.eia.gov/opendata/register.php).

Set your API key in one of two ways:
- Add it to a `.env` file as `EIA_API_KEY=your_token`
- Or pass it directly as a parameter: `EIAClient(api_key="your_token")`

## Usage Example

See [examples/1_Generic/steps/1_Download.ipynb](examples/1_Generic/steps/1_Download.ipynb) for usage instructions and examples.

## License

MIT License 