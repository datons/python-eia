"""CLI tests using Typer's test runner."""

import pytest
from typer.testing import CliRunner

from eia.cli.app import app

runner = CliRunner()


class TestCLIHelp:
    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_routes(self):
        result = runner.invoke(app, ["routes"])
        assert result.exit_code == 0
        assert "electricity" in result.output.lower()

    def test_meta(self):
        result = runner.invoke(app, ["meta", "electricity/rto/fuel-type-data"])
        assert result.exit_code == 0

    def test_catalog_routes(self):
        result = runner.invoke(app, ["catalog", "routes"])
        assert result.exit_code == 0

    def test_catalog_recipes(self):
        result = runner.invoke(app, ["catalog", "recipes"])
        assert result.exit_code == 0
        assert "lng-exports-europe" in result.output

    def test_catalog_show(self):
        result = runner.invoke(app, ["catalog", "show", "natural-gas/move/expc"])
        assert result.exit_code == 0
        assert "EVE" in result.output

    def test_catalog_recipe(self):
        result = runner.invoke(app, ["catalog", "recipe", "lng-exports-europe"])
        assert result.exit_code == 0


@pytest.mark.integration
class TestCLIIntegration:
    def test_get_data(self):
        result = runner.invoke(
            app,
            [
                "get",
                "electricity/rto/fuel-type-data",
                "--facet", "respondent=US48",
                "--facet", "fueltype=SUN",
                "--start", "2024-06-01",
                "--end", "2024-06-02",
                "--frequency", "hourly",
                "--data", "value",
            ],
        )
        assert result.exit_code == 0, result.output
