"""
Bot kirish nuqtasi — ishga tushirish.
"""

import asyncio
import logging
import sys
import os

from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot.config import get_settings
from bot.database.db import init_db
from bot.middlewares.db_middleware import DatabaseMiddleware

# Handlerlar
from bot.handlers import start, checkpoint, history, objects_list, help, settings, admin

# Sozlamalar
config = get_settings()


async def health_check(request):
    """Dummy health check HTTP endpoint for Render"""
    return web.Response(text="Bot is running!")

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

    # Webhook or Polling
    webhook_url = os.environ.get("RENDER_EXTERNAL_URL", config.WEBHOOK_URL)
    port = int(os.environ.get("PORT", 8080))

    if webhook_url:
        # WEBHOOK MODE
        webhook_path = "/webhook"
        full_webhook_url = f"{webhook_url.rstrip('/')}{webhook_path}"
        logger.info(f"🌐 Webhook mode: {full_webhook_url}")

        app = web.Application()
        SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        ).register(app, path=webhook_path)
        setup_application(app, dp, bot=bot)

        # Set webhook
        await bot.set_webhook(full_webhook_url, drop_pending_updates=True)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"🌐 HTTP server listening on {port}")
        
        # Keep process alive
        await asyncio.Event().wait()
    else:
        # POLLING MODE & Dummy HTTP server
        logger.info("🔁 Polling mode")
        app = web.Application()
        app.router.add_get("/", health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"🌐 Dummy HTTP server running on {port}")

        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
        finally:
            await bot.session.close()
            await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
