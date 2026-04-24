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

PER_PAGE = 10


@router.message(F.text == "📋 Tarix")
async def show_history(message: Message, state: FSMContext):
    user_id = message.from_user.id
    print(f"▶️ [DEBUG] 📋 Tarix bosildi. User: {user_id}")
    await state.clear()

    checkpoints = checkpoint_service.get_user_history(user_id, limit=50)
    print(f"▶️ [DEBUG] User history rows: {len(checkpoints)}")

    if not checkpoints:
        await message.answer(
            "📋 Tarixingiz\n\nHozircha checkpoint yo'q.",
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


def _format_time(created_at_str: str) -> str:
    if not created_at_str:
        return "?"
    try:
        dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        local_time = dt + timedelta(hours=5)
        return local_time.strftime("%d.%m.%Y %H:%M")
    except:
        return created_at_str


def _format_purpose(raw_purpose: str) -> str:
    if "Pelesos" in raw_purpose:
        return f"🧹 Ish turi: {raw_purpose}"
    elif "Promifka" in raw_purpose:
        return f"💧 Ish turi: {raw_purpose}"
    return raw_purpose


def _format_history(checkpoints, page: int, total: int) -> str:
    text = f"📋 Tarixingiz ({total} ta)\n\n"

    start_idx = (page - 1) * PER_PAGE
    end_idx = start_idx + PER_PAGE
    page_data = checkpoints[start_idx:end_idx]

    for i, cp in enumerate(page_data, start=start_idx + 1):
        time_str = _format_time(cp.get("created_at"))
        purpose = _format_purpose(cp.get("purpose", "Nomalum"))
        status_icon = "✅" if cp.get("status") == "Keldi" else "❌"

        text += (
            f"{i}. 🏗 Obyekt: <b>{cp.get('object_name', '?')}</b>\n"
            f"   📌 Status: {cp.get('status', '?')} {status_icon}\n"
            f"   {purpose}\n"
            f"   🕒 Vaqt: {time_str}\n\n"
        )

    return text
