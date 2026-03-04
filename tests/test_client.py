"""Unit and integration tests for the EIA client."""

import os

import pandas as pd
import pytest

from eia.client import Data, EIAClient


class TestClientInit:
    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("EIA_API_KEY", raising=False)
        with pytest.raises(ValueError, match="API key is required"):
            EIAClient(api_key=None)


class TestFormatGapDate:
    def test_monthly(self):
        ts = pd.Timestamp("2024-06-15")
        assert Data._format_gap_date(ts, "monthly") == "2024-06"

    def test_annual(self):
        ts = pd.Timestamp("2024-06-15")
        assert Data._format_gap_date(ts, "annual") == "2024"

    def test_daily(self):
        ts = pd.Timestamp("2024-06-15")
        assert Data._format_gap_date(ts, "daily") == "2024-06-15"

    def test_none_frequency(self):
        ts = pd.Timestamp("2024-06-15")
        assert Data._format_gap_date(ts, None) == "2024-06-15"


@pytest.mark.integration
class TestDataEndpoint:
    def test_get_data_endpoint_returns_data(self, client):
        data = client.get_data_endpoint("electricity/rto/fuel-type-data")
        assert isinstance(data, Data)
        assert data.name

    def test_get_returns_dataframe(self, data_endpoint):
        df = data_endpoint.get(
            facets={"respondent": "US48", "fueltype": "SUN"},
            frequency="hourly",
            start="2024-06-01",
            end="2024-06-02",
            data_columns=["value"],
        )
        assert isinstance(df, pd.DataFrame)
        assert "value" in df.columns
        assert len(df) > 0

    def test_tz_aware_period_slicing(self, data_endpoint):
        """Regression: tz-aware period column should not crash on date slicing."""
        df = data_endpoint.get(
            facets={"respondent": "US48", "fueltype": "SUN"},
            frequency="hourly",
            start="2024-06-01",
            end="2024-06-02",
            data_columns=["value"],
        )
        # If we got here without error, the tz-aware slicing works
        assert isinstance(df, pd.DataFrame)
