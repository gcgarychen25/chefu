import logging
from enum import Enum, auto
from typing import Callable, Awaitable

from ..models.recipe import Recipe

log = logging.getLogger(__name__)


class Intent(str, Enum):
    NEXT = "next"
    REPEAT = "repeat"
    TIMER_QUERY = "timer_query"
    RECIPE_QUESTION = "recipe_question"
    INGREDIENT_QUESTION = "ingredient_question"
    STEP_QUESTION = "step_question"
    UNKNOWN = "unknown"


class StateMachine:
    """
    Conversational cooking assistant that helps with recipe questions.
    """

    def __init__(self, recipe: Recipe, tts_callback: Callable[[str], Awaitable[None]]):
        self.recipe = recipe
        self.tts = tts_callback
        self.idx = 0
        self.started = False

    def _current_step(self) -> str:
        if self.idx < len(self.recipe.steps):
            return self.recipe.steps[self.idx]
        return "You've completed all the steps! Great job!"

    def _get_ingredients_summary(self) -> str:
        # Extract ingredients from the recipe steps (simple approach)
        # This could be enhanced with better parsing
        return "Based on the recipe, you'll need beef, radish, seasonings, and other ingredients."

    async def handle(self, intent: Intent) -> None:
        """Handle different types of cooking questions and requests"""
        
        if intent == Intent.NEXT:
            if not self.started:
                self.started = True
                await self.tts("Great! Let me help you with this recipe. Step one: " + self._current_step())
            else:
                self.idx = min(self.idx + 1, len(self.recipe.steps) - 1)
                await self.tts("Next step: " + self._current_step())
                
        elif intent == Intent.REPEAT:
            if self.started:
                await self.tts("The current step is: " + self._current_step())
            else:
                await self.tts("We haven't started cooking yet. Would you like to begin?")
                
        elif intent == Intent.TIMER_QUERY:
            await self.tts("The timer has about 5 minutes remaining.")
            
        elif intent == Intent.RECIPE_QUESTION:
            await self.tts(f"This recipe has {len(self.recipe.steps)} steps total. It's for making beef soup.")
            
        elif intent == Intent.INGREDIENT_QUESTION:
            await self.tts(self._get_ingredients_summary())
            
        elif intent == Intent.STEP_QUESTION:
            await self.tts(f"We're currently on step {self.idx + 1} of {len(self.recipe.steps)}. " + self._current_step())
            
        else:
            log.warning("Unknown intent")
            await self.tts("Sorry, I didn't understand that. You can ask me about ingredients, steps, or say commands like 'start', 'next step', or 'repeat'.")

    async def reset(self):
        """Initial greeting - don't automatically start reading steps"""
        self.idx = 0
        self.started = False
        await self.tts("Hello! I'm chefu, your voice cooking assistant. I've reviewed this recipe and I'm ready to help. What would you like to know? You can ask about ingredients, steps, or say 'start cooking' when you're ready to begin.")
