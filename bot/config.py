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

    # Admin — Telegram user ID lari (vergul bilan ajratilgan string)
    ADMIN_IDS: str = "1282014621"

    @property
    def admin_ids_list(self) -> list[int]:
        try:
            ids = [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]
        except:
            ids = []
        # Jarima admini har doim admin hisoblanadi
        if self.FINE_ADMIN_ID and self.FINE_ADMIN_ID not in ids:
            ids.append(self.FINE_ADMIN_ID)
        return ids

    # ── Jarima tizimi ──
    # Obyekt boshlanish sanasi so'raladigan va jarimalar bo'yicha mas'ul admin
    FINE_ADMIN_ID: int = 82167016
    FINE_ADMIN_USERNAME: str = "A70906"
    # Jarima miqdori ($) va davr (kun)
    FINE_AMOUNT: int = 50
    FINE_PERIOD_DAYS: int = 7
    # Muddat tugashiga necha kun qolganda ishchiga eslatma yuboriladi
    FINE_WARN_DAYS: int = 2

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
