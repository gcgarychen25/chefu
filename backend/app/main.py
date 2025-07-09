from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .api.websocket import router as ws_router
from .core.config import get_settings

settings = get_settings()
app = FastAPI(title="ChefBud‑Voice", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)

# Serve PWA
app.mount("/", StaticFiles(directory="frontend/static", html=True), name="static")
