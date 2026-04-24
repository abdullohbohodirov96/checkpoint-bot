"""
Admin handlerlari.
"""

from datetime import datetime, timezone, timedelta

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.config import get_settings
from bot.states.states import AdminAddObjectStates
from bot.services.checkpoint_service import CheckpointService
from bot.keyboards.admin_kb import (
    admin_menu_kb,
    admin_objects_delete_kb,
    confirm_delete_kb,
    admin_history_mode_kb,
    admin_history_objects_kb,
    admin_history_pagination_kb,
)

settings = get_settings()
router = Router(name="admin")
checkpoint_service = CheckpointService()

HISTORY_PER_PAGE = 20


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids_list


# ──────────────────────────────────────────
# TEST CHANNEL
# ──────────────────────────────────────────

@router.message(Command("testchannel"))
async def test_channel_cmd(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
        
    try:
        await bot.send_message(chat_id=settings.CHANNEL_ID, text="TEST XABAR")
        await message.answer("✅ Kanalga test xabar yuborildi.")
        print("✅ Kanalga test xabar yuborildi.")
    except Exception as e:
        await message.answer(f"❌ Kanal yuborishda xato: {e}")
        print(f"❌ Kanalga xabar yuborishda xato: {e}")


# ──────────────────────────────────────────
# OBYEKTLAR RO'YXATI
# ──────────────────────────────────────────

@router.message(F.text == "🏗 Obyektlar ro'yxati")
async def list_objects(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    objects = checkpoint_service.get_all_objects()

    if objects is None:
        await message.answer("⚠️ Obyektlarni yuklashda xatolik yuz berdi.")
        return

    if not objects:
        await message.answer("📋 Hech qanday obyekt yo'q.")
        return

    text = "🏗 <b>Obyektlar ro'yxati</b>\n\n"
    for i, obj in enumerate(objects, 1):
        text += (
            f"{i}. <b>{obj['name']}</b>\n"
            f"   📍 {obj['latitude']}, {obj['longitude']}\n"
            f"   📏 Radius: {obj.get('radius', 500)} m\n\n"
        )
    text += f"Jami: {len(objects)} ta"

    await message.answer(text, parse_mode="HTML")


# ──────────────────────────────────────────
# MANZIL QO'SHISH
# ──────────────────────────────────────────

@router.message(F.text == "➕ Manzil qo'shish")
async def add_object_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    await state.set_state(AdminAddObjectStates.entering_name)
    await message.answer("📝 Obyekt nomini kiriting:")


@router.message(AdminAddObjectStates.entering_name)
async def add_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(name=message.text.strip())
    await state.set_state(AdminAddObjectStates.entering_coordinates)
    await message.answer(
        f"✅ Nomi: <b>{message.text.strip()}</b>\n\n"
        "📍 Koordinatani kiriting:\n"
        "Masalan: <code>41.390166, 69.271265</code>",
        parse_mode="HTML",
    )


@router.message(AdminAddObjectStates.entering_coordinates)
async def add_coordinates(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    text = message.text.strip()
    try:
        parts = text.split(',')
        if len(parts) != 2:
            raise ValueError
        
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
        
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri! Format quyidagicha bo'lishi kerak:\n41.390166, 69.271265")
        return

    data = await state.get_data()

    obj = checkpoint_service.add_object(
        name=data["name"],
        latitude=lat,
        longitude=lon,
        radius=500,
    )

    await state.clear()
    
    if obj is None:
        await message.answer("❌ Obyektni saqlashda xatolik yuz berdi.")
        return

    await message.answer(
        f"✅ <b>Obyekt muvaffaqiyatli qo'shildi!</b>\n\n"
        f"🏗 {obj['name']}\n"
        f"📍 {obj['latitude']}, {obj['longitude']}\n"
        f"📏 Radius: {obj.get('radius', 500)} m",
        parse_mode="HTML",
    )


# ──────────────────────────────────────────
# MANZILNI O'CHIRISH
# ──────────────────────────────────────────

@router.message(F.text == "🗑 Manzilni o'chirish")
async def delete_object_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    objects = checkpoint_service.get_all_objects()

    if not objects:
        await message.answer("📋 Hech qanday obyekt yo'q.")
        return

    await message.answer(
        "🗑 <b>Qaysi obyektni o'chirish kerak?</b>",
        parse_mode="HTML",
        reply_markup=admin_objects_delete_kb(objects),
    )


@router.callback_query(F.data.startswith("admin:delete_confirm:"))
async def delete_confirm(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    object_id = int(callback.data.split(":")[2])
    obj = checkpoint_service.get_object_by_id(object_id)

    if not obj:
        await callback.answer("❌ Topilmadi!", show_alert=True)
        return

    await callback.message.edit_text(
        f"🗑 <b>{obj['name']}</b> ni o'chirmoqchimisiz?\n\n"
        "⚠️ Bu amalni ortga qaytarib bo'lmaydi!",
        parse_mode="HTML",
        reply_markup=confirm_delete_kb(object_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:do_delete:"))
async def do_delete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    object_id = int(callback.data.split(":")[2])
    obj = checkpoint_service.get_object_by_id(object_id)
    name = obj['name'] if obj else "?"

    deleted = checkpoint_service.delete_object(object_id)

    if deleted:
        await callback.message.edit_text(f"✅ <b>{name}</b> o'chirildi!", parse_mode="HTML")
    else:
        await callback.message.edit_text("❌ Obyekt topilmadi!")

    await callback.answer()


# ──────────────────────────────────────────
# CHECKPOINTLAR TARIXI — MODE TANLASH
# ──────────────────────────────────────────

@router.message(F.text == "📋 Checkpointlar tarixi")
async def admin_history_start(message: Message, state: FSMContext):
    print(f"▶️ [DEBUG] Admin bossa: 📋 Checkpointlar tarixi. User: {message.from_user.id}")
    if not is_admin(message.from_user.id):
        print(f"❌ [DEBUG] Ruxsat bekor qilindi (admin emas): {message.from_user.id}")
        return

    await state.clear()
    await message.answer(
        "📋 <b>Checkpointlar tarixi</b>\n\nQanday ko'rmoqchisiz?",
        parse_mode="HTML",
        reply_markup=admin_history_mode_kb(),
    )


# ──────────────────────────────────────────
# ADMIN TARIX — GENERAL
# ──────────────────────────────────────────

@router.callback_query(F.data == "admin:history_mode:general")
async def admin_history_general(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    print(f"▶️ [DEBUG] Admin history mode: GENERAL. User: {callback.from_user.id}")
    checkpoints = checkpoint_service.get_all_history(limit=50)

    if not checkpoints:
        await callback.message.edit_text(
            "📋 Barcha checkpointlar\n\nHozircha hech qanday checkpoint yo'q."
        )
        await callback.answer()
        return

    total_pages = (len(checkpoints) + HISTORY_PER_PAGE - 1) // HISTORY_PER_PAGE
    text = _format_admin_history(checkpoints, page=1, total=len(checkpoints))

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=admin_history_pagination_kb(1, total_pages),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:history_page:"))
async def admin_history_page(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    page = int(callback.data.split(":")[2])
    checkpoints = checkpoint_service.get_all_history(limit=50)

    if not checkpoints:
        await callback.answer("Tarix topilmadi")
        return

    total_pages = (len(checkpoints) + HISTORY_PER_PAGE - 1) // HISTORY_PER_PAGE
    
    if page > total_pages:
        page = total_pages

    text = _format_admin_history(checkpoints, page=page, total=len(checkpoints))

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=admin_history_pagination_kb(page, total_pages),
    )
    await callback.answer()


# ──────────────────────────────────────────
# ADMIN TARIX — LOCATION BO'YICHA
# ──────────────────────────────────────────

@router.callback_query(F.data == "admin:history_mode:location")
async def admin_history_location(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    print(f"▶️ [DEBUG] Admin history mode: LOCATION. User: {callback.from_user.id}")
    objects = checkpoint_service.get_all_objects()
    print(f"▶️ [DEBUG] Objects count: {len(objects) if objects else 0}")

    if not objects:
        await callback.message.edit_text("📋 Hech qanday obyekt yo'q.")
        await callback.answer()
        return

    await callback.message.edit_text(
        "📍 <b>Qaysi manzil bo'yicha tarix ko'rmoqchisiz?</b>",
        parse_mode="HTML",
        reply_markup=admin_history_objects_kb(objects),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:history_obj:"))
async def admin_history_by_object(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    object_name = callback.data.split(":", 2)[2]
    print(f"▶️ [DEBUG] Admin history by object: '{object_name}'")

    checkpoints = checkpoint_service.get_history_by_object(object_name, limit=50)

    if not checkpoints:
        await callback.message.edit_text(
            f"📍 Location bo'yicha tarix\n"
            f"🏗 Obyekt: {object_name}\n\n"
            f"Bu manzil bo'yicha checkpointlar yo'q."
        )
        await callback.answer()
        return

    text = f"📍 <b>Location bo'yicha tarix</b>\n🏗 Obyekt: <b>{object_name}</b>\n\n"
    for i, cp in enumerate(checkpoints, 1):
        time_str = _format_time(cp.get("created_at"))
        purpose = _format_purpose(cp.get("purpose", "Nomalum"))

        text += (
            f"{i}. 👤 User: {cp.get('username', '?')}\n"
            f"   📌 Status: {cp.get('status', '?')} {'✅' if cp.get('status') == 'Keldi' else '❌'}\n"
            f"   {purpose}\n"
            f"   🕒 Vaqt: {time_str}\n\n"
        )

    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:history_back")
async def admin_history_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        "📋 <b>Checkpointlar tarixi</b>\n\nQanday ko'rmoqchisiz?",
        parse_mode="HTML",
        reply_markup=admin_history_mode_kb(),
    )
    await callback.answer()


# ──────────────────────────────────────────
# FORMATTING HELPERS
# ──────────────────────────────────────────

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


def _format_admin_history(checkpoints, page: int, total: int) -> str:
    text = f"📋 <b>Barcha checkpointlar</b> ({total} ta)\n\n"

    start_idx = (page - 1) * HISTORY_PER_PAGE
    end_idx = start_idx + HISTORY_PER_PAGE
    page_data = checkpoints[start_idx:end_idx]

    for i, cp in enumerate(page_data, start=start_idx + 1):
        time_str = _format_time(cp.get("created_at"))
        purpose = _format_purpose(cp.get("purpose", "Nomalum"))
        status_icon = "✅" if cp.get("status") == "Keldi" else "❌"

        text += (
            f"{i}. 👤 User: {cp.get('username', '?')}\n"
            f"   🏗 Obyekt: <b>{cp.get('object_name', '?')}</b>\n"
            f"   📌 Status: {cp.get('status', '?')} {status_icon}\n"
            f"   {purpose}\n"
            f"   🕒 Vaqt: {time_str}\n\n"
        )

    return text
