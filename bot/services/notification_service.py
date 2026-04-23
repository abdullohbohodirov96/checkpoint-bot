"""
Admin xabar yuborish xizmati.
Har bir muvaffaqiyatli checkpoint dan so'ng admin ga xabar yuboriladi.
"""

from datetime import timedelta

from aiogram import Bot

from bot.config import get_settings
from bot.models.models import Checkpoint, User, Object

settings = get_settings()


class NotificationService:
    """Admin ga checkpoint bildirishnomalarini yuborish"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.channel_id = settings.CHANNEL_ID

    async def notify_checkpoint(
        self,
        user: User,
        obj: Object,
        checkpoint: Checkpoint,
        is_accepted: bool,
    ) -> bool:
        """
        Checkpoint urinishi haqida kanalga xabar yuborish.
        """
        if not self.channel_id:
            return False

        # Vaqt — UTC+5 (Toshkent)
        local_time = checkpoint.checked_at + timedelta(hours=5)
        time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")

        if is_accepted:
            text = (
                "✅ Yangi checkpoint\n"
                f"Ishchi: {user.display_name}\n"
                f"Telegram ID: {user.telegram_id}\n"
                f"Obyekt: {obj.name}\n"
                f"Vaqt: {time_str}\n"
                f"Koordinata: {checkpoint.user_latitude:.6f}, {checkpoint.user_longitude:.6f}\n"
                "Status: Keldi"
            )
        else:
            text = (
                "❌ Noto'g'ri checkpoint\n"
                f"Ishchi: {user.display_name}\n"
                f"Telegram ID: {user.telegram_id}\n"
                f"Tanlangan obyekt: {obj.name}\n"
                f"Vaqt: {time_str}\n"
                f"Koordinata: {checkpoint.user_latitude:.6f}, {checkpoint.user_longitude:.6f}\n"
                "Status: Manzilga kelmadi"
            )

        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=text,
            )
            return True
        except Exception as e:
            print(f"⚠️ Admin ga xabar yuborishda xato: {e}")
            return False
