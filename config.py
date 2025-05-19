from pydantic import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    redis_url: str
    cache_ttl: int
    rate_limit: int
    api_key_secret: str

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
