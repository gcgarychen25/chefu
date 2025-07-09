import asyncio
import logging
from datetime import timedelta
from typing import Dict, Callable, Awaitable

from ..models.recipe import Recipe, Timer

log = logging.getLogger(__name__)


class TimerManager:
    def __init__(self, recipe: Recipe, tts_cb: Callable[[str], Awaitable[None]]):
        self.recipe = recipe
        self.tts = tts_cb
        self.tasks: Dict[str, asyncio.Task] = {}

    def start_all(self):
        for timer in self.recipe.timers:
            task = asyncio.create_task(self._countdown(timer))
            self.tasks[timer.label] = task

    async def _countdown(self, timer: Timer):
        seconds = int(timer.duration.total_seconds())
        await asyncio.sleep(seconds)
        await self.tts(f"{timer.label} timer finished! {seconds // 60} minutes are up.")

    async def cancel_all(self):
        for task in self.tasks.values():
            task.cancel()
        self.tasks.clear()
