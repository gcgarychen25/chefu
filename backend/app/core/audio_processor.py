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
        audio = np.frombuffer(pcm_bytes, dtype=np.float32)
        audio_24k = resampy.resample(
            audio,
            self.settings.sampling_rate_in,
            self.settings.sampling_rate_out,
        )
        return audio_24k.astype(np.float32).tobytes()

    async def stream_chunks(self, websocket):
        """
        Async generator: receives binary frames from WS,
        yields resampled bytes.
        """
        while True:
            pcm = await websocket.receive_bytes()
            yield self.downsample(pcm)
