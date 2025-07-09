from __future__ import annotations

from datetime import timedelta
from typing import List, Optional

from pydantic import BaseModel, conint


class Timer(BaseModel):
    label: str
    duration: timedelta
    remaining_sec: conint(ge=0) = 0


class Recipe(BaseModel):
    title: str
    steps: List[str]
    timers: List[Timer] = []
