"""
Foydalanuvchi checkpoint tarixini ko'rish.
"""

from datetime import timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.checkpoint_service import CheckpointService
from bot.services.user_service import UserService
from bot.keyboards.user_kb import history_pagination_kb

router = Router(name="history")

PER_PAGE = 5


@router.message(F.text == "📋 Mening tarixim")
async def show_history(message: Message, session: AsyncSession, state: FSMContext):
    """Foydalanuvchi checkpoint tarixini ko'rsatish"""
    await state.clear()

    user_service = UserService(session)
    user = await user_service.get_user_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("❌ /start buyrug'ini yuboring.")
        return

    checkpoint_service = CheckpointService(session)
    total = await checkpoint_service.get_user_checkpoint_count(user.id)

    if total == 0:
        await message.answer(
            "📋 <b>Tarixingiz</b>\n\nHozircha checkpoint yo'q.",
            parse_mode="HTML",
        )
        return

    checkpoints = await checkpoint_service.get_user_history(user.id, limit=PER_PAGE, offset=0)
    total_pages = (total + PER_PAGE - 1) // PER_PAGE
    text = _format_history(checkpoints, page=1, total=total)

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=history_pagination_kb(1, total_pages),
    )


@router.callback_query(F.data.startswith("history_page:"))
async def history_page(callback: CallbackQuery, session: AsyncSession):
    """Sahifalarni almashtirish"""
    page = int(callback.data.split(":")[1])

    user_service = UserService(session)
    user = await user_service.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Xatolik!")
        return

    checkpoint_service = CheckpointService(session)
    total = await checkpoint_service.get_user_checkpoint_count(user.id)
    total_pages = (total + PER_PAGE - 1) // PER_PAGE

    offset = (page - 1) * PER_PAGE
    checkpoints = await checkpoint_service.get_user_history(user.id, limit=PER_PAGE, offset=offset)
    text = _format_history(checkpoints, page=page, total=total)

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=history_pagination_kb(page, total_pages),
    )
    await callback.answer()


def _format_history(checkpoints, page: int, total: int) -> str:
    text = f"📋 <b>Mening tarixim</b> ({total} ta)\n\n"

    for i, cp in enumerate(checkpoints, start=(page - 1) * PER_PAGE + 1):
        local_time = cp.checked_at + timedelta(hours=5)
        time_str = local_time.strftime("%d.%m.%Y %H:%M")
        status_icon = "✅" if cp.status == "accepted" else "❌"
        obj_name = cp.object.name if cp.object else "?"

        text += (
            f"{i}. {status_icon} <b>{obj_name}</b>\n"
            f"   📏 {cp.distance_in_meters:.0f} m | 🕐 {time_str}\n\n"
        )

    return text
