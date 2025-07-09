from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging

from .api.websocket import router as ws_router
from .core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

settings = get_settings()
app = FastAPI(title="chefu", version="0.1.0", description="Voice-activated cooking assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include WebSocket router BEFORE static files mount
app.include_router(ws_router)

# Add a test endpoint to verify API routing works
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "chefu API is running", "openai_configured": bool(settings.openai_api_key)}

# Serve PWA static files (this should be LAST)
app.mount("/", StaticFiles(directory="frontend/static", html=True), name="static")
