from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
import logging
import asyncio

from ..core.audio_processor import AudioProcessor
from ..core.state_machine import StateMachine, Intent
from ..core.timer_manager import TimerManager
from ..services.openai_client import OpenAIRealtimeClient
from ..services.recipe_parser import RecipeParser

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    audio_processor = AudioProcessor()

    # Client must send the raw recipe first (text)
    raw_recipe = await ws.receive_text()
    recipe = await RecipeParser.parse(raw_recipe)

    async def tts(text: str):
        # Push to browser; client plays speech synthesis
        if ws.application_state == WebSocketState.CONNECTED:
            await ws.send_json({"tts": text})

    sm = StateMachine(recipe, tts)
    timers = TimerManager(recipe, tts)
    timers.start_all()
    await sm.reset()

    async with OpenAIRealtimeClient() as openai_ws:
        async def pump_audio():
            async for pcm in audio_processor.stream_chunks(ws):
                await openai_ws.push_audio(pcm)

        async def handle_deltas():
            async for delta in openai_ws.receive_text_deltas():
                await ws.send_json({"delta": delta})
                # TODO: Intent classification → for now every utterance = NEXT
                await sm.handle(Intent.NEXT)

        try:
            await asyncio.gather(pump_audio(), handle_deltas())
        except WebSocketDisconnect:
            log.info("Client disconnected")
        finally:
            await timers.cancel_all()
