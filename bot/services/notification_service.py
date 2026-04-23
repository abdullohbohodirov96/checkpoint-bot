"""
Xabar yuborish xizmati.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from aiogram import Bot
from bot.config import get_settings

settings = get_settings()

class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.channel_id = settings.CHANNEL_ID

    async def notify_checkpoint(
        self,
        checkpoint: Dict[str, Any],
        is_accepted: bool,
    ) -> bool:
        if not self.channel_id:
            return False

        # Supabase returns created_at as ISO string, e.g. "2026-04-23T14:55:00.000000+00:00"
        created_at_str = checkpoint.get("created_at")
        if created_at_str:
            # simple parse
            try:
                dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                local_time = dt + timedelta(hours=5)
                time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
            except:
                time_str = created_at_str
        else:
            local_time = datetime.now(timezone.utc) + timedelta(hours=5)
            time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")

        if is_accepted:
            text = (
                "✅ Yangi checkpoint\n"
                f"Ishchi: {checkpoint['username']}\n"
                f"Telegram ID: {checkpoint['user_id']}\n"
                f"Obyekt: {checkpoint['object_name']}\n"
                f"Vaqt: {time_str}\n"
                f"Koordinata: {checkpoint['latitude']:.6f}, {checkpoint['longitude']:.6f}\n"
                "Status: Keldi"
            )
        else:
            text = (
                "❌ Noto'g'ri checkpoint\n"
                f"Ishchi: {checkpoint['username']}\n"
                f"Telegram ID: {checkpoint['user_id']}\n"
                f"Tanlangan obyekt: {checkpoint['object_name']}\n"
                f"Vaqt: {time_str}\n"
                f"Koordinata: {checkpoint['latitude']:.6f}, {checkpoint['longitude']:.6f}\n"
                "Status: Manzilga kelmadi"
            )

        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=text,
            )
            return True
        except Exception as e:
            print(f"⚠️ Kanalga xabar yuborishda xato: {e}")
            return False
