"""
OpenAI Realtime API client implementation.
Based on official OpenAI Realtime API documentation.
"""

import json
import logging
import base64
import asyncio
import websockets
from websockets.legacy.client import WebSocketClientProtocol

from ..core.config import get_settings

log = logging.getLogger(__name__)
MODEL = "gpt-4o-realtime-preview-2024-12-17"


class OpenAIRealtimeClient:
    def __init__(self):
        self.settings = get_settings()
        self.ws: WebSocketClientProtocol | None = None
        self.session_id = None

    async def __aenter__(self):
        # Official OpenAI Realtime API endpoint with model parameter
        url = f"wss://api.openai.com/v1/realtime?model={MODEL}"
        
        log.info(f"🔗 Connecting to OpenAI Realtime API: {url}")
        
        self.ws = await websockets.connect(
            url,
            extra_headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "OpenAI-Beta": "realtime=v1"
            },
            max_size=4 * 1024 * 1024,
        )
        
        log.info("✅ Connected to OpenAI Realtime API")
        
        # Wait for session.created event
        initial_event = await self.ws.recv()
        session_created = json.loads(initial_event)
        
        if session_created.get("type") == "session.created":
            self.session_id = session_created["session"]["id"]
            log.info(f"✅ Session created: {self.session_id}")
        else:
            log.error(f"❌ Expected session.created, got: {session_created}")
            
        # Configure session for audio input/output
        await self._send({
            "type": "session.update",
            "session": {
                "modalities": ["audio", "text"],
                "instructions": "You are a helpful cooking assistant. Respond naturally to cooking questions and commands.",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                    "create_response": True
                },
                "temperature": 0.8
            }
        })
        
        # Wait for session.updated confirmation
        session_updated = await self.ws.recv()
        updated_event = json.loads(session_updated)
        
        if updated_event.get("type") == "session.updated":
            log.info("✅ Session configured successfully")
        else:
            log.warning(f"⚠️ Expected session.updated, got: {updated_event}")
            
        return self

    async def __aexit__(self, *exc):
        if self.ws:
            await self.ws.close()
            log.info("🔌 Disconnected from OpenAI Realtime API")

    async def _send(self, message: dict):
        if not self.ws:
            raise RuntimeError("WebSocket not connected")
        await self.ws.send(json.dumps(message))
        log.debug(f"📤 Sent: {message['type']}")

    async def push_audio(self, pcm_bytes: bytes):
        """Push PCM audio bytes to the input audio buffer"""
        if not pcm_bytes:
            return
            
        # Convert PCM bytes to base64
        audio_base64 = base64.b64encode(pcm_bytes).decode('utf-8')
        
        await self._send({
            "type": "input_audio_buffer.append",
            "audio": audio_base64
        })

    async def receive_text_deltas(self):
        """
        Async iterator yielding incremental text symbols from responses.
        """
        if not self.ws:
            raise RuntimeError("WebSocket not connected")
            
        log.info("📝 Starting to receive events from OpenAI")
        
        async for msg in self.ws:
            try:
                data = json.loads(msg)
                event_type = data.get("type", "unknown")
                
                log.debug(f"📨 Received event: {event_type}")
                
                # Handle different event types
                if event_type == "response.audio_transcript.delta":
                    # Text transcript of the audio response
                    if delta := data.get("delta"):
                        yield delta
                        
                elif event_type == "response.text.delta":
                    # Direct text response
                    if delta := data.get("delta"):
                        yield delta
                        
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    # User speech transcription completed
                    if transcription := data.get("transcript"):
                        log.info(f"🎯 User speech transcribed: '{transcription}'")
                        # This should be sent back to frontend for display
                        yield f"[TRANSCRIPTION: {transcription}]"
                        
                elif event_type == "conversation.item.input_audio_transcription.failed":
                    log.warning("❌ Speech transcription failed")
                    
                elif event_type == "input_audio_buffer.speech_started":
                    log.info("🗣️ OpenAI detected speech start")
                    
                elif event_type == "input_audio_buffer.speech_stopped":
                    log.info("🤫 OpenAI detected speech end")
                    
                elif event_type == "input_audio_buffer.committed":
                    log.info("✅ Audio buffer committed")
                    
                elif event_type == "conversation.item.created":
                    if item := data.get("item"):
                        log.info(f"💬 Conversation item created: {item.get('type')} from {item.get('role', 'unknown')}")
                        # Check if this is a user message with transcription
                        if item.get("role") == "user" and item.get("content"):
                            for content in item.get("content", []):
                                if content.get("type") == "input_audio" and content.get("transcript"):
                                    transcript = content.get("transcript")
                                    log.info(f"🎯 User message transcribed: '{transcript}'")
                                    yield f"[USER SAID: {transcript}]"
                        
                elif event_type == "response.created":
                    log.info("🚀 Response generation started")
                    
                elif event_type == "response.done":
                    log.info("✅ Response generation completed")
                    
                elif event_type == "error":
                    error = data.get("error", {})
                    log.error(f"❌ OpenAI API error: {error}")
                    yield f"[ERROR: {error}]"
                    
                else:
                    log.debug(f"📋 Unhandled event type: {event_type}")
                    # Log full event data for unhandled events to debug
                    if event_type not in ["rate_limits.updated"]:
                        log.debug(f"📋 Full event data: {data}")
                    
            except json.JSONDecodeError as e:
                log.error(f"❌ Failed to parse JSON message: {e}")
            except Exception as e:
                log.error(f"❌ Error processing message: {e}")
                # If we get a connection close, re-raise it
                if "1005" in str(e) or "CloseCode" in str(e):
                    log.error("🔌 OpenAI connection closed unexpectedly")
                    raise
