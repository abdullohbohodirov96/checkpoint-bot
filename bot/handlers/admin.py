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
    admin_history_pagination_kb,
)

settings = get_settings()
router = Router(name="admin")
checkpoint_service = CheckpointService()

HISTORY_PER_PAGE = 10


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids_list


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


@router.message(F.text == "📋 Checkpointlar tarixi")
async def admin_history(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    checkpoints = checkpoint_service.get_all_history(limit=50) # simplify pagination for dict

    if not checkpoints:
        await message.answer("📋 Barcha checkpointlar\n\nHozircha hech qanday checkpoint yo'q.")
        return

    total_pages = (len(checkpoints) + HISTORY_PER_PAGE - 1) // HISTORY_PER_PAGE
    text = _format_admin_history(checkpoints, page=1, total=len(checkpoints))

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=admin_history_pagination_kb(1, total_pages),
    )


@router.callback_query(F.data.startswith("admin:history_page:"))
async def admin_history_page(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    page = int(callback.data.split(":")[2])
    checkpoints = checkpoint_service.get_all_history(limit=50)
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


def _format_admin_history(checkpoints, page: int, total: int) -> str:
    text = f"📋 <b>Barcha checkpointlar</b> ({total} ta eng oxirgi)\n\n"

    start_idx = (page - 1) * HISTORY_PER_PAGE
    end_idx = start_idx + HISTORY_PER_PAGE
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

        user_name = cp.get("username", "?")
        obj_name = cp.get("object_name", "?")
        raw_purpose = cp.get('purpose', 'Nomalum')
        if "Pelesos" in raw_purpose:
            purpose = f"🧹 {raw_purpose}"
        elif "Promifka" in raw_purpose:
            purpose = f"💧 {raw_purpose}"
        else:
            purpose = raw_purpose

        text += (
            f"{i}. 👤 User: {user_name}\n"
            f"   🏗 Obyekt: <b>{obj_name}</b>\n"
            f"   📌 Status: {status_icon}\n"
            f"   {purpose}\n"
            f"   🕒 Vaqt: {time_str}\n\n"
        )

    return text
