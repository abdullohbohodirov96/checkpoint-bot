"""
/start va asosiy menyu handleri.
"""

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.config import get_settings
from bot.keyboards.user_kb import main_menu_kb
from bot.keyboards.admin_kb import admin_menu_kb

settings = get_settings()
router = Router(name="start")


def get_menu_kb(telegram_id: int):
    """Foydalanuvchiga mos menyuni qaytaradi"""
    if telegram_id in settings.admin_ids_list:
        return admin_menu_kb()
    return main_menu_kb()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    /start — menyuni ko'rsatish.
    """
    await state.clear()
    
    is_admin = message.from_user.id in settings.admin_ids_list
    print(f"▶️ [DEBUG] /start bosildi. User: {message.from_user.id}, IsAdmin: {is_admin}, Admins: {settings.admin_ids_list}")

    # Foydalanuvchi nomi
    full_name = message.from_user.first_name or ""
    if message.from_user.last_name:
        full_name += f" {message.from_user.last_name}"
    full_name = full_name.strip() or "Foydalanuvchi"

    text = (
        f"👋 Assalomu alaykum, <b>{full_name}</b>!\n\n"
        "📍 <b>Checkpoint Bot</b> ga xush kelibsiz!\n\n"
        "Ish joyingizga kelganingizni tasdiqlash uchun "
        "<b>Checkpoint qilish</b> tugmasini bosing."
    )

    await message.answer(
        text=text,
        parse_mode="HTML",
        reply_markup=get_menu_kb(message.from_user.id),
    )
