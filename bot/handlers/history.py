"""
Foydalanuvchi checkpoint tarixini ko'rish.
"""

from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.services.checkpoint_service import CheckpointService
from bot.keyboards.user_kb import history_pagination_kb

router = Router(name="history")
checkpoint_service = CheckpointService()

PER_PAGE = 5


@router.message(F.text == "📋 Mening tarixim")
async def show_history(message: Message, state: FSMContext):
    await state.clear()

    checkpoints = checkpoint_service.get_user_history(message.from_user.id, limit=50)

    if not checkpoints:
        await message.answer(
            "📋 <b>Tarixingiz</b>\n\nHozircha checkpoint yo'q.",
            parse_mode="HTML",
        )
        return

    total_pages = (len(checkpoints) + PER_PAGE - 1) // PER_PAGE
    text = _format_history(checkpoints, page=1, total=len(checkpoints))

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=history_pagination_kb(1, total_pages),
    )


@router.callback_query(F.data.startswith("history_page:"))
async def history_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])

    checkpoints = checkpoint_service.get_user_history(callback.from_user.id, limit=50)
    
    if not checkpoints:
        await callback.answer("❌ Tarix topilmadi")
        return

    total_pages = (len(checkpoints) + PER_PAGE - 1) // PER_PAGE
    if page > total_pages: page = total_pages

    text = _format_history(checkpoints, page=page, total=len(checkpoints))

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=history_pagination_kb(page, total_pages),
    )
    await callback.answer()


def _format_history(checkpoints, page: int, total: int) -> str:
    text = f"📋 <b>Mening tarixim</b> ({total} ta eng oxirgi)\n\n"

    start_idx = (page - 1) * PER_PAGE
    end_idx = start_idx + PER_PAGE
    page_data = checkpoints[start_idx:end_idx]

    for i, cp in enumerate(page_data, start=start_idx + 1):
        created_at_str = cp.get("created_at")
        if created_at_str:
            try:
                dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                local_time = dt + timedelta(hours=5)
                time_str = local_time.strftime("%d.%m.%Y %H:%M")
            except:
                time_str = created_at_str
        else:
            time_str = "?"

        status_icon = "✅" if cp.get("status") == "Keldi" else "❌"
        obj_name = cp.get("object_name", "?")

        text += (
            f"{i}. {status_icon} <b>{obj_name}</b>\n"
            f"   🕐 {time_str}\n\n"
        )

    return text
