from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: Literal["DEV", "TEST", "PAPER", "PROD"] = "PAPER"
    database_url: str = "postgresql+psycopg://cats:cats@localhost:5432/cats_v2e"
    log_level: str = "INFO"

    alpaca_api_key: str | None = None
    alpaca_api_secret: str | None = None
    alpaca_paper_base_url: str = "https://paper-api.alpaca.markets"

    model_config = SettingsConfigDict(
        env_prefix="CATS_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
