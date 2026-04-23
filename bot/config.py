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

    # Database — SQLite (default) yoki PostgreSQL
    # SQLite: sqlite+aiosqlite:///checkpoint.db
    # PostgreSQL: postgresql+asyncpg://user:pass@host:port/db
    DATABASE_URL: str = "sqlite+aiosqlite:///checkpoint.db"

    # Admin — Telegram user ID (raqam)
    ADMIN_TELEGRAM_ID: int = 1282014621

    # Kanal yoki Gruppa ID
    CHANNEL_ID: int = -5175061069

    DEFAULT_RADIUS: int = 500

    WEBHOOK_URL: str = ""

    @property
    def async_database_url(self) -> str:
        """DATABASE_URL ni asyncpg formatiga o'zgartirish (faqat PostgreSQL uchun)"""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Sozlamalarni cache qilib qaytaradi"""
    return Settings()
