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
        photo_id: str
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

        raw_purpose = checkpoint.get('purpose', 'Nomalum')
        if "Pelesos" in raw_purpose:
            purpose_str = f"🧹 {raw_purpose}"
        elif "Promifka" in raw_purpose:
            purpose_str = f"💧 {raw_purpose}"
        else:
            purpose_str = raw_purpose

        header = "✅ Yangi checkpoint" if is_accepted else "❌ Noto'g'ri checkpoint"
        status_str = "Keldi" if is_accepted else "Kelmadi"

        text = (
            f"{header}\n\n"
            f"👤 Ishchi: {checkpoint.get('username', '?')}\n"
            f"🆔 ID: {checkpoint.get('user_id', '?')}\n"
            f"🏗 Obyekt: {checkpoint.get('object_name', '?')}\n"
            f"{purpose_str}\n"
            f"🕒 Vaqt: {time_str}\n"
            f"📍 Koordinata: {checkpoint.get('latitude', 0):.6f}, {checkpoint.get('longitude', 0):.6f}\n"
            f"📌 Status: {status_str}"
        )

        try:
            await self.bot.send_photo(
                chat_id=self.channel_id,
                photo=photo_id,
                caption=text,
            )
            return True
        except Exception as e:
            print(f"⚠️ Kanalga xabar yuborishda xato: {e}")
            return False
