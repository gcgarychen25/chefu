import asyncio
from backend.app.services.recipe_parser import RecipeParser


def test_regex_parse():
    text = "1. step one\n2) step two"

    async def run():
        return await RecipeParser.parse(text)

    recipe = asyncio.run(run())
    assert recipe.steps == ["step one", "step two"]


def test_fallback_parse():
    text = "step one\nstep two"

    async def run():
        return await RecipeParser.parse(text)

    recipe = asyncio.run(run())
    assert recipe.steps == ["step one", "step two"]
