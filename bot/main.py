"""
Bot kirish nuqtasi — ishga tushirish.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from bot.config import get_settings
from bot.database.db import init_db
from bot.middlewares.db_middleware import DatabaseMiddleware

# Handlerlar
from bot.handlers import start, checkpoint, history, objects_list, help, settings, admin

# Sozlamalar
config = get_settings()


async def main():
    """Botni ishga tushirish"""

    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    logger = logging.getLogger(__name__)

    # Sozlamalarni tekshirish
    if not config.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN topilmadi! .env fayliga yozing.")
        sys.exit(1)

    if not config.ADMIN_TELEGRAM_ID:
        logger.warning("⚠️ ADMIN_TELEGRAM_ID sozlanmagan! Admin funksiyalari ishlamaydi.")

    # Database
    logger.info("📊 Database jadvallar yaratilmoqda...")
    await init_db()

    # Bot va Dispatcher
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware — DB session
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())

    # Routerlarni ro'yxatdan o'tkazish
    dp.include_routers(
        start.router,
        checkpoint.router,
        history.router,
        objects_list.router,
        help.router,
        settings.router,
        admin.router,
    )

    # Bot ma'lumotlarini olish
    bot_info = await bot.get_me()
    logger.info(f"✅ Bot ishga tushdi: @{bot_info.username}")
    logger.info(f"🔑 Admin Telegram ID: {config.ADMIN_TELEGRAM_ID}")

    # Polling boshlash
    try:
        # Eski update larni o'tkazib yuborish
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
