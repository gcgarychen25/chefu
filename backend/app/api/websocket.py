from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
import logging
import asyncio
import re

from ..core.audio_processor import AudioProcessor
from ..core.state_machine import StateMachine, Intent
from ..core.timer_manager import TimerManager
from ..services.openai_client import OpenAIRealtimeClient
from ..services.recipe_parser import RecipeParser
from ..core.config import get_settings

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


def classify_intent(text: str) -> Intent:
    """Simple keyword-based intent classification for English cooking commands"""
    text = text.lower().strip()
    
    # Next step keywords
    if any(keyword in text for keyword in ["next step", "next", "continue", "start", "begin", "go", "proceed"]):
        return Intent.NEXT
    
    # Repeat keywords  
    if any(keyword in text for keyword in ["repeat", "again", "what", "current", "now", "say that again"]):
        return Intent.REPEAT
        
    # Timer related
    if any(keyword in text for keyword in ["timer", "time", "how long", "how much time", "minutes", "remaining"]):
        return Intent.TIMER_QUERY
        
    # Ingredient questions
    if any(keyword in text for keyword in ["ingredients", "what do i need", "what ingredients", "shopping", "buy", "materials"]):
        return Intent.INGREDIENT_QUESTION
        
    # Recipe overview questions
    if any(keyword in text for keyword in ["how many steps", "steps", "how to make", "recipe", "overview", "process"]):
        return Intent.RECIPE_QUESTION
        
    # Current step questions
    if any(keyword in text for keyword in ["which step", "what step", "where are we", "progress", "current step"]):
        return Intent.STEP_QUESTION
    
    return Intent.UNKNOWN


@router.websocket("/test")
async def test_websocket(websocket: WebSocket):
    """Simple test WebSocket endpoint to verify connection works"""
    await websocket.accept()
    try:
        await websocket.send_json({"message": "WebSocket connection successful! 🎉"})
        
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "echo": f"Received: {data}",
                "timestamp": str(asyncio.get_event_loop().time())
            })
    except WebSocketDisconnect:
        log.info("Test WebSocket disconnected")


@router.websocket("/ws-simple")
async def simple_websocket_test(ws: WebSocket):
    """Simple WebSocket test that echoes back messages for debugging"""
    log.info("🔗 Simple WebSocket test connection")
    await ws.accept()
    log.info("✅ Simple WebSocket connection accepted")
    
    try:
        # Handle recipe text first (like main handler)
        log.info("⏳ Waiting for recipe text...")
        recipe_text = await ws.receive_text()
        log.info(f"📝 Received recipe: {len(recipe_text)} characters")
        await ws.send_json({"type": "recipe_received", "tts": "Recipe received! I'm ready to help you cook."})
        
        # Handle READY signal
        log.info("⏳ Waiting for READY signal...")
        ready_signal = await ws.receive_text()
        log.info(f"📨 Received signal: '{ready_signal}'")
        
        if ready_signal == "READY":
            await ws.send_json({"type": "ready_confirmed", "tts": "Great! I'm listening. Try saying something!"})
        
        message_count = 0
        audio_count = 0
        
        while True:
            try:
                if ws.application_state == WebSocketState.CONNECTED:
                    # Use receive() to get any type of message
                    try:
                        message = await asyncio.wait_for(ws.receive(), timeout=0.1)
                        
                        # Check if it's text or bytes
                        if message["type"] == "websocket.receive" and "text" in message:
                            text_data = message["text"]
                            message_count += 1
                            log.info(f"📨 Received text message #{message_count}: {text_data[:100]}")
                            
                            # Echo back
                            await ws.send_json({
                                "type": "echo", 
                                "message": f"Received text #{message_count}: {text_data[:50]}",
                                "tts": f"I heard you say message number {message_count}"
                            })
                            
                        elif message["type"] == "websocket.receive" and "bytes" in message:
                            audio_data = message["bytes"]
                            audio_count += 1
                            if audio_count % 10 == 0:  # Log every 10th audio chunk
                                log.info(f"🎵 Received audio chunk #{audio_count}, size: {len(audio_data)} bytes")
                                await ws.send_json({
                                    "type": "audio_received",
                                    "chunk_number": audio_count,
                                    "size": len(audio_data),
                                    "tts": f"I'm receiving your audio! Chunk {audio_count} received."
                                })
                        else:
                            log.debug(f"🤔 Unknown message type: {message}")
                            
                    except asyncio.TimeoutError:
                        # No messages, continue
                        await asyncio.sleep(0.1)
                        
            except WebSocketDisconnect:
                log.info("👋 Simple WebSocket client disconnected")
                break
            except Exception as e:
                log.error(f"💥 Simple WebSocket error: {e}")
                await ws.send_json({"type": "error", "message": str(e)})
                
    except Exception as e:
        log.error(f"💥 Simple WebSocket handler error: {e}")
        import traceback
        log.error(f"📋 Simple WebSocket traceback: {traceback.format_exc()}")
        

@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    log.info("🔗 New WebSocket connection attempt")
    await ws.accept()
    log.info("✅ WebSocket connection accepted")
    
    # Check if OpenAI API key is configured
    settings = get_settings()
    if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
        log.error("❌ OpenAI API key not configured")
        await ws.send_json({
            "error": "OpenAI API key not configured. Please set OPENAI_API_KEY in your .env file."
        })
        await ws.close()
        return
    
    log.info("✅ OpenAI API key configured")
    
    # Test OpenAI API key with a simple validation
    try:
        import openai
        test_client = openai.OpenAI(api_key=settings.openai_api_key)
        # Simple test to validate API key
        models = test_client.models.list()
        log.info("✅ OpenAI API key validation successful")
    except Exception as api_test_error:
        log.error(f"❌ OpenAI API key validation failed: {api_test_error}")
        await ws.send_json({
            "error": f"OpenAI API key validation failed: {str(api_test_error)}"
        })
        await ws.close()
        return
    
    try:
        audio_processor = AudioProcessor()
        log.info("✅ Audio processor created")

        # Client must send the raw recipe first (text)
        log.info("⏳ Waiting for recipe text from client...")
        raw_recipe = await ws.receive_text()
        log.info(f"✅ Received recipe: {len(raw_recipe)} characters")
        
        recipe = await RecipeParser.parse(raw_recipe)
        log.info(f"✅ Recipe parsed: {len(recipe.steps)} steps")

        async def tts(text: str):
            # Push to browser; client plays speech synthesis
            log.info(f"🔊 Sending TTS message: '{text[:100]}{'...' if len(text) > 100 else ''}'")
            if ws.application_state == WebSocketState.CONNECTED:
                await ws.send_json({"tts": text})
                log.info("✅ TTS message sent successfully")
            else:
                log.warning("❌ WebSocket not connected, TTS message dropped")

        sm = StateMachine(recipe, tts)
        timers = TimerManager(recipe, tts)
        timers.start_all()
        log.info("✅ State machine and timers initialized")
        
        # Wait for microphone ready signal from frontend
        log.info("⏳ Waiting for READY signal from client...")
        ready_signal = await ws.receive_text()
        log.info(f"📨 Received signal: '{ready_signal}'")
        
        if ready_signal == "READY":
            log.info("🎯 Starting conversation...")
            # Now start the conversation
            await sm.reset()
        else:
            log.warning(f"⚠️ Expected 'READY' signal, got: '{ready_signal}'")

        log.info("🔗 Connecting to OpenAI Realtime API...")
        try:
            async with OpenAIRealtimeClient() as openai_ws:
                log.info("✅ OpenAI WebSocket connected successfully")
                
                async def pump_audio():
                    log.info("🎤 Starting audio pump...")
                    chunk_count = 0
                    try:
                        async for pcm in audio_processor.stream_chunks(ws):
                            chunk_count += 1
                            if chunk_count % 50 == 0:  # Log every 50th chunk to avoid spam
                                log.info(f"🎵 Processed {chunk_count} audio chunks, sending to OpenAI...")
                            
                            try:
                                await openai_ws.push_audio(pcm)
                                if chunk_count % 50 == 0:
                                    log.info(f"✅ Successfully sent chunk {chunk_count} to OpenAI")
                            except Exception as audio_error:
                                log.error(f"❌ Failed to send audio chunk {chunk_count}: {audio_error}")
                                
                    except Exception as pump_error:
                        log.error(f"💥 Audio pump error: {pump_error}")
                        raise

                async def handle_deltas():
                    log.info("📝 Starting text delta handler...")
                    current_text = ""
                    delta_count = 0
                    transcription_count = 0
                    response_count = 0
                    
                    try:
                        async for delta in openai_ws.receive_text_deltas():
                            delta_count += 1
                            
                            # Handle different types of deltas
                            if delta.startswith("[TRANSCRIPTION:"):
                                transcription_count += 1
                                log.info(f"🎯 User transcription #{transcription_count}: {delta}")
                                # Send transcription to frontend for display
                                await ws.send_json({"transcription": delta[15:-1]})  # Remove [TRANSCRIPTION: and ]
                                
                            elif delta.startswith("[USER SAID:"):
                                log.info(f"🎯 User speech processed: {delta}")
                                await ws.send_json({"user_speech": delta[12:-1]})  # Remove [USER SAID: and ]
                                
                            elif delta.startswith("[ERROR:"):
                                log.error(f"❌ OpenAI API error: {delta}")
                                await ws.send_json({"error": delta})
                                
                            else:
                                # Regular response text delta
                                response_count += 1
                                current_text += delta
                                await ws.send_json({"delta": delta})
                                
                                if response_count <= 10:  # Log first 10 response deltas
                                    log.info(f"📝 AI response delta #{response_count}: '{delta}'")
                                elif response_count == 11:
                                    log.info("📝 (Continuing to receive AI response deltas...)")
                            
                            # Process complete sentences for intent classification (only for AI responses)
                            if not delta.startswith("[") and delta in [".", "?", "!", ","] or len(current_text) > 50:
                                if current_text.strip():
                                    intent = classify_intent(current_text)
                                    log.info(f"🎯 Classified intent: {intent} for text: '{current_text.strip()}'")
                                    try:
                                        await sm.handle(intent)
                                        log.info(f"✅ Successfully handled intent: {intent}")
                                    except Exception as intent_error:
                                        log.error(f"❌ Error handling intent {intent}: {intent_error}")
                                current_text = ""
                                
                    except Exception as delta_error:
                        log.error(f"💥 Delta handler error: {delta_error}")
                        import traceback
                        log.error(f"📋 Delta handler traceback: {traceback.format_exc()}")
                        # Send error to frontend
                        await ws.send_json({"error": f"Response processing error: {str(delta_error)}"})
                        raise

                log.info("🚀 Starting audio processing tasks...")
                try:
                    await asyncio.gather(pump_audio(), handle_deltas())
                except WebSocketDisconnect:
                    log.info("👋 Client disconnected normally")
                except Exception as e:
                    log.error(f"💥 Error in processing tasks: {e}")
                    import traceback
                    log.error(f"📋 Full traceback: {traceback.format_exc()}")
                finally:
                    await timers.cancel_all()
                    log.info("🛑 Timers cancelled")
                    
        except Exception as openai_error:
            log.error(f"💥 OpenAI connection error: {openai_error}")
            import traceback
            log.error(f"📋 Full OpenAI error traceback: {traceback.format_exc()}")
            await ws.send_json({"error": f"OpenAI connection failed: {str(openai_error)}"})
            
    except Exception as e:
        log.error(f"💥 WebSocket error: {e}")
        import traceback
        log.error(f"📋 Full error traceback: {traceback.format_exc()}")
        await ws.send_json({"error": f"Server error: {str(e)}"})
        await ws.close()
