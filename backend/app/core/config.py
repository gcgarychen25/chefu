from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    openai_api_key: str = ""
    sampling_rate_in: int = 48_000
    sampling_rate_out: int = 24_000

    model_config = {
        "env_file": ".env",
        "env_prefix": "",
        "extra": "ignore",
    }

@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
