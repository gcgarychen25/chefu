"""
Tiny wrapper around OpenAI realtime websocket API.
Keeps interface very small so the rest of the codebase
can be swapped to a different provider later.
"""

import json
import logging
import os
import websockets
from websockets.legacy.client import WebSocketClientProtocol

from ..core.config import get_settings

log = logging.getLogger(__name__)
MODEL = "gpt-4o-realtime-preview"


class OpenAIRealtimeClient:
    def __init__(self):
        self.settings = get_settings()
        self.ws: WebSocketClientProtocol | None = None

    async def __aenter__(self):
        # Official endpoint 2025‑Q3; adjust when GA.
        url = "wss://api.openai.com/v1/audio/realtime"
        self.ws = await websockets.connect(
            url,
            extra_headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
            max_size=4 * 1024 * 1024,
        )
        await self._send({"model": MODEL})
        return self

    async def __aexit__(self, *exc):
        if self.ws:
            await self.ws.close()

    async def _send(self, message: dict):
        assert self.ws
        await self.ws.send(json.dumps(message))

    async def push_audio(self, pcm24k: bytes):
        await self._send({"audio": pcm24k})

    async def receive_text_deltas(self):
        """
        Async iterator yielding incremental text symbols.
        """
        assert self.ws
        async for msg in self.ws:
            data = json.loads(msg)
            if delta := data.get("response", {}).get("text", {}).get("delta"):
                yield delta
