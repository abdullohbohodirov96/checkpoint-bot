"""
Loyiha konfiguratsiyasi.
Barcha sozlamalar .env faylidan o'qiladi.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Asosiy sozlamalar"""

    # Telegram Bot
    BOT_TOKEN: str = ""

    # Supabase Database
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # Admin — Telegram user ID (raqam)
    ADMIN_TELEGRAM_ID: int = 1282014621

    # Kanal yoki Gruppa ID
    CHANNEL_ID: int = -5175061069

    DEFAULT_RADIUS: int = 500

    WEBHOOK_URL: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Sozlamalarni cache qilib qaytaradi"""
    return Settings()
