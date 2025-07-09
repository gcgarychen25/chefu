import logging
from enum import Enum, auto
from typing import Callable

from ..models.recipe import Recipe

log = logging.getLogger(__name__)


class Intent(str, Enum):
    NEXT = "next"
    REPEAT = "repeat"
    TIMER_QUERY = "timer_query"
    UNKNOWN = "unknown"


class StateMachine:
    """
    Holds current step index, routes intents, emits TTS strings.
    """

    def __init__(self, recipe: Recipe, tts_callback: Callable[[str], None]):
        self.recipe = recipe
        self.tts = tts_callback
        self.idx = 0

    def _current_step(self) -> str:
        return self.recipe.steps[self.idx]

    async def handle(self, intent: Intent) -> None:
        if intent == Intent.NEXT:
            self.idx = min(self.idx + 1, len(self.recipe.steps) - 1)
        elif intent == Intent.REPEAT:
            pass  # stay
        elif intent == Intent.TIMER_QUERY:
            # naïve for prototype
            self.tts("还有五分钟。")
            return
        else:
            log.warning("Unknown intent")

        self.tts(self._current_step())

    async def reset(self):
        self.idx = 0
        self.tts(self._current_step())
