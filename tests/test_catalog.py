"""Unit tests for the EIA data catalog."""

import pytest
from eia.catalog import ROUTES, RECIPES, get_route, get_recipe, summary


class TestRoutes:
    def test_routes_nonempty(self):
        assert len(ROUTES) > 0

    def test_get_route_known(self):
        info = get_route("electricity/rto/fuel-type-data")
        assert info.name
        assert info.frequency

    def test_get_route_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown route"):
            get_route("does/not/exist")


class TestRecipes:
    def test_recipes_nonempty(self):
        assert len(RECIPES) > 0

    def test_get_recipe_known(self):
        recipe = get_recipe("lng-exports-europe")
        assert recipe.route
        assert recipe.frequency

    def test_get_recipe_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown recipe"):
            get_recipe("nonexistent-recipe")

    def test_each_recipe_has_valid_route(self):
        for recipe_id, recipe in RECIPES.items():
            assert recipe.route in ROUTES, (
                f"Recipe '{recipe_id}' references unknown route '{recipe.route}'"
            )

    def test_each_recipe_has_facets_and_frequency(self):
        for recipe_id, recipe in RECIPES.items():
            assert recipe.facets, f"Recipe '{recipe_id}' has no facets"
            assert recipe.frequency, f"Recipe '{recipe_id}' has no frequency"

    def test_lng_europe_recipe_uses_eve(self):
        """The LNG exports recipe must use process=EVE (by vessel), not ENG."""
        recipe = get_recipe("lng-exports-europe")
        assert recipe.facets.get("process") == "EVE"


class TestSummary:
    def test_summary_nonempty(self):
        s = summary()
        assert isinstance(s, str)
        assert len(s) > 100
