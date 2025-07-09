"""
Prototype – regex first, fallback to GPT‑4 for robustness.
"""

import re
from typing import List

from ..models.recipe import Recipe


class RecipeParser:
    step_pattern = re.compile(r"^\s*\d+[.\)]\s*(.*)$", re.M)

    @classmethod
    async def parse(cls, raw: str) -> Recipe:
        steps: List[str] = []
        for match in cls.step_pattern.finditer(raw):
            steps.append(match.group(1).strip())

        if not steps:
            # Fallback to trivial split
            steps = [line.strip() for line in raw.splitlines() if line.strip()]

        # Timer extraction left as exercise
        return Recipe(title="Untitled", steps=steps)
