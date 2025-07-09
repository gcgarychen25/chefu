import asyncio
import pytest
from backend.app.core.state_machine import StateMachine, Intent
from backend.app.models.recipe import Recipe

@pytest.mark.asyncio
async def test_next_intent_advances_step():
    spoken = []

    def cb(text): spoken.append(text)

    r = Recipe(title="Eggs", steps=["one", "two"])
    sm = StateMachine(r, cb)
    await sm.reset()
    await sm.handle(Intent.NEXT)
    assert spoken[-1] == "two"
