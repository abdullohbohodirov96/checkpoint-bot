"""
Database middleware — har bir handler ga DB session yuboradi.
"""

from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.database.db import async_session


class DatabaseMiddleware(BaseMiddleware):
    """
    Har bir handler chaqirilganda yangi DB session ochadi
    va handler tugagandan so'ng yopadi.

    Handler ichida `session` parametri orqali foydalanish:
        async def my_handler(message: Message, session: AsyncSession):
            ...
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
