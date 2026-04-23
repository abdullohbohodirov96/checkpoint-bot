"""
Foydalanuvchi boshqaruv xizmati.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.models.models import User

settings = get_settings()


class UserService:
    """User CRUD operatsiyalari"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> User:
        """
        Foydalanuvchini topadi yoki yangi yaratadi.
        Admin ID ga mos kelsa role='admin' qilinadi.
        """
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Ma'lumotlarni yangilash
            if username is not None:
                user.username = username
            if full_name is not None:
                user.full_name = full_name
            # Admin tekshirish
            if telegram_id == settings.ADMIN_TELEGRAM_ID and user.role != "admin":
                user.role = "admin"
            await self.session.flush()
            return user

        # Yangi user yaratish
        role = "admin" if telegram_id == settings.ADMIN_TELEGRAM_ID else "worker"
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            role=role,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Telegram ID orqali user topish"""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
