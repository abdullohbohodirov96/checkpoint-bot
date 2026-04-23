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
        self.admin_id = settings.ADMIN_TELEGRAM_ID

    async def notify_checkpoint(
        self,
        user: User,
        obj: Object,
        checkpoint: Checkpoint,
    ) -> bool:
        """
        Muvaffaqiyatli checkpoint haqida admin ga xabar yuborish.
        """
        if not self.admin_id:
            return False

        # Vaqt — UTC+5 (Toshkent)
        local_time = checkpoint.checked_at + timedelta(hours=5)
        time_str = local_time.strftime("%Y-%m-%d %H:%M")

        text = (
            "✅ <b>Yangi checkpoint</b>\n\n"
            f"Ishchi: {user.display_name}\n"
            f"Telegram ID: <code>{user.telegram_id}</code>\n"
            f"Obyekt: {obj.name}\n"
            f"Vaqt: {time_str}\n"
            f"Koordinata: {checkpoint.user_latitude:.6f}, {checkpoint.user_longitude:.6f}\n"
            f"Masofa: {checkpoint.distance_in_meters:.0f} m\n"
            f"Status: Keldi"
        )

        try:
            await self.bot.send_message(
                chat_id=self.admin_id,
                text=text,
                parse_mode="HTML",
            )
            return True
        except Exception as e:
            print(f"⚠️ Admin ga xabar yuborishda xato: {e}")
            return False
