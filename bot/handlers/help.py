"""
Yordam va admin bilan aloqa handlerlari.
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.config import get_settings

settings = get_settings()
router = Router(name="help")


@router.message(F.text == "❓ Yordam")
async def show_help(message: Message, state: FSMContext):
    """Yordam"""
    await state.clear()

    text = (
        "❓ <b>Botdan qanday foydalanish</b>\n\n"
        "1. <b>Checkpoint qilish</b> tugmasini bosing\n"
        "2. Ro'yxatdan obyektni tanlang\n"
        "3. Joylashuvingizni yuboring\n"
        "4. Bot masofani tekshiradi\n\n"
        "✅ 500 metr ichida — checkpoint qabul\n"
        "❌ Uzoqda — rad etiladi\n\n"
        "📋 <b>Mening tarixim</b> — barcha checkpointlaringiz\n\n"
        f"💰 <b>Jarima qoidasi</b>\n"
        f"Har bir obyektda har {settings.FINE_PERIOD_DAYS} kunda (ayrim obyektlarda admin belgilagan muddatda) "
        "kamida 1 marta checkpoint bo'lishi shart. "
        f"Bo'lmasa mas'ul ishchiga {settings.FINE_AMOUNT}$ jarima yoziladi. "
        "Batafsil: «💰 Jarimalarim» tugmasi."
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "📞 Admin bilan aloqa")
async def contact_admin(message: Message, state: FSMContext):
    """Admin bilan aloqa"""
    await state.clear()

    if settings.admin_ids_list:
        text = (
            "📞 <b>Admin bilan aloqa</b>\n\n"
            f"<a href='tg://user?id={settings.admin_ids_list[0]}'>Admin ga yozish</a>"
        )
    else:
        text = "⚠️ Admin hali sozlanmagan."

    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
