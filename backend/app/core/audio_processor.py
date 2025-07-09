"""
Down‑samples browser PCM chunks (48 kHz mono float32) to 24 kHz
and yields bytes ready for OpenAI streaming.
"""

import numpy as np
import resampy
import soundfile as sf

from .config import get_settings


class AudioProcessor:
    def __init__(self) -> None:
        self.settings = get_settings()

    def downsample(self, pcm_bytes: bytes) -> bytes:
        # Convert browser float32 PCM to numpy array
        audio = np.frombuffer(pcm_bytes, dtype=np.float32)
        
        # Resample from 48kHz to 24kHz
        audio_24k = resampy.resample(
            audio,
            self.settings.sampling_rate_in,
            self.settings.sampling_rate_out,
        )
        
        # Convert float32 to int16 PCM for OpenAI (pcm16 format)
        # Clamp to [-1, 1] range and scale to int16 range
        audio_clamped = np.clip(audio_24k, -1.0, 1.0)
        audio_int16 = (audio_clamped * 32767).astype(np.int16)
        
        return audio_int16.tobytes()

    async def stream_chunks(self, websocket):
        """
        Async generator: receives binary frames from WS,
        yields resampled bytes.
        """
        while True:
            pcm = await websocket.receive_bytes()
            yield self.downsample(pcm)
