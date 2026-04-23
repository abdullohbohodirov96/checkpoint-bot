"""
Admin handlerlari.
Doimiy reply keyboard tugmalari bilan ishlaydi.
Faqat ADMIN_TELEGRAM_ID ga ega foydalanuvchi ishlatadi.
"""

from datetime import timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

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

HISTORY_PER_PAGE = 10


def is_admin(user_id: int) -> bool:
    return user_id == settings.ADMIN_TELEGRAM_ID


# ══════════════════════════════════════════
# OBYEKTLAR RO'YXATI
# ══════════════════════════════════════════

@router.message(F.text == "🏗 Obyektlar ro'yxati")
async def list_objects(message: Message, session: AsyncSession, state: FSMContext):
    """Barcha obyektlarni ko'rsatish"""
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    service = CheckpointService(session)
    objects = await service.get_all_objects()

    if not objects:
        await message.answer("📋 Hech qanday obyekt yo'q.")
        return

    text = "🏗 <b>Obyektlar ro'yxati</b>\n\n"
    for i, obj in enumerate(objects, 1):
        text += (
            f"{i}. <b>{obj.name}</b>\n"
            f"   📍 {obj.latitude}, {obj.longitude}\n"
            f"   📏 Radius: {obj.radius} m\n\n"
        )
    text += f"Jami: {len(objects)} ta"

    await message.answer(text, parse_mode="HTML")


# ══════════════════════════════════════════
# YANGI OBYEKT QO'SHISH
# ══════════════════════════════════════════

@router.message(F.text == "➕ Yangi obyekt qo'shish")
async def add_object_start(message: Message, state: FSMContext):
    """Yangi obyekt qo'shishni boshlash"""
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
    await state.set_state(AdminAddObjectStates.entering_latitude)
    await message.answer(
        f"✅ Nomi: <b>{message.text.strip()}</b>\n\n"
        "📍 Latitude (kenglik) ni kiriting:\n"
        "<i>Misol: 41.390166</i>",
        parse_mode="HTML",
    )


@router.message(AdminAddObjectStates.entering_latitude)
async def add_latitude(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        lat = float(message.text.strip())
        if not (-90 <= lat <= 90):
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri! Raqam kiriting (-90 dan 90 gacha).\nMisol: 41.390166")
        return

    await state.update_data(latitude=lat)
    await state.set_state(AdminAddObjectStates.entering_longitude)
    await message.answer(
        f"✅ Latitude: <b>{lat}</b>\n\n"
        "📍 Longitude (uzunlik) ni kiriting:\n"
        "<i>Misol: 69.271265</i>",
        parse_mode="HTML",
    )


@router.message(AdminAddObjectStates.entering_longitude)
async def add_longitude(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        lon = float(message.text.strip())
        if not (-180 <= lon <= 180):
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri! Raqam kiriting (-180 dan 180 gacha).\nMisol: 69.271265")
        return

    await state.update_data(longitude=lon)
    await state.set_state(AdminAddObjectStates.entering_radius)
    await message.answer(
        f"✅ Longitude: <b>{lon}</b>\n\n"
        "📏 Radiusni kiriting (metrda):\n"
        "<i>Misol: 500</i>",
        parse_mode="HTML",
    )


@router.message(AdminAddObjectStates.entering_radius)
async def add_radius(message: Message, session: AsyncSession, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        radius = int(message.text.strip())
        if radius <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri! Musbat butun son kiriting.\nMisol: 500")
        return

    data = await state.get_data()
    service = CheckpointService(session)

    obj = await service.add_object(
        name=data["name"],
        latitude=data["latitude"],
        longitude=data["longitude"],
        radius=radius,
    )

    await state.clear()
    await message.answer(
        f"✅ <b>Obyekt muvaffaqiyatli qo'shildi!</b>\n\n"
        f"🏗 {obj.name}\n"
        f"📍 {obj.latitude}, {obj.longitude}\n"
        f"📏 Radius: {obj.radius} m",
        parse_mode="HTML",
    )


# ══════════════════════════════════════════
# OBYEKTNI O'CHIRISH
# ══════════════════════════════════════════

@router.message(F.text == "🗑 Obyektni o'chirish")
async def delete_object_start(message: Message, session: AsyncSession, state: FSMContext):
    """O'chirish uchun obyektlar ro'yxati"""
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    service = CheckpointService(session)
    objects = await service.get_all_objects()

    if not objects:
        await message.answer("📋 Hech qanday obyekt yo'q.")
        return

    await message.answer(
        "🗑 <b>Qaysi obyektni o'chirish kerak?</b>",
        parse_mode="HTML",
        reply_markup=admin_objects_delete_kb(objects),
    )


@router.callback_query(F.data.startswith("admin:delete_confirm:"))
async def delete_confirm(callback: CallbackQuery, session: AsyncSession):
    """Tasdiqlash so'rash"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    object_id = int(callback.data.split(":")[2])
    service = CheckpointService(session)
    obj = await service.get_object_by_id(object_id)

    if not obj:
        await callback.answer("❌ Topilmadi!", show_alert=True)
        return

    await callback.message.edit_text(
        f"🗑 <b>{obj.name}</b> ni o'chirmoqchimisiz?\n\n"
        "⚠️ Bu amalni ortga qaytarib bo'lmaydi!",
        parse_mode="HTML",
        reply_markup=confirm_delete_kb(object_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:do_delete:"))
async def do_delete(callback: CallbackQuery, session: AsyncSession):
    """O'chirishni amalga oshirish"""
    if not is_admin(callback.from_user.id):
        return

    object_id = int(callback.data.split(":")[2])
    service = CheckpointService(session)

    obj = await service.get_object_by_id(object_id)
    name = obj.name if obj else "?"

    deleted = await service.delete_object(object_id)

    if deleted:
        await callback.message.edit_text(f"✅ <b>{name}</b> o'chirildi!", parse_mode="HTML")
    else:
        await callback.message.edit_text("❌ Obyekt topilmadi!")

    await callback.answer()


# ══════════════════════════════════════════
# CHECKPOINTLAR TARIXI (ADMIN)
# ══════════════════════════════════════════

@router.message(F.text == "📊 Checkpointlar tarixi")
async def admin_history(message: Message, session: AsyncSession, state: FSMContext):
    """Barcha checkpoint tarixini ko'rsatish"""
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    service = CheckpointService(session)
    total = await service.get_all_checkpoint_count()

    if total == 0:
        await message.answer("📊 Hozircha checkpoint yo'q.")
        return

    checkpoints = await service.get_all_history(limit=HISTORY_PER_PAGE, offset=0)
    total_pages = (total + HISTORY_PER_PAGE - 1) // HISTORY_PER_PAGE
    text = _format_admin_history(checkpoints, page=1, total=total)

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=admin_history_pagination_kb(1, total_pages),
    )


@router.callback_query(F.data.startswith("admin:history_page:"))
async def admin_history_page(callback: CallbackQuery, session: AsyncSession):
    """Sahifalash"""
    if not is_admin(callback.from_user.id):
        return

    page = int(callback.data.split(":")[2])
    service = CheckpointService(session)
    total = await service.get_all_checkpoint_count()
    total_pages = (total + HISTORY_PER_PAGE - 1) // HISTORY_PER_PAGE

    offset = (page - 1) * HISTORY_PER_PAGE
    checkpoints = await service.get_all_history(limit=HISTORY_PER_PAGE, offset=offset)
    text = _format_admin_history(checkpoints, page=page, total=total)

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=admin_history_pagination_kb(page, total_pages),
    )
    await callback.answer()


def _format_admin_history(checkpoints, page: int, total: int) -> str:
    text = f"📊 <b>Checkpointlar tarixi</b> ({total} ta)\n\n"

    for i, cp in enumerate(checkpoints, start=(page - 1) * HISTORY_PER_PAGE + 1):
        local_time = cp.checked_at + timedelta(hours=5)
        time_str = local_time.strftime("%d.%m.%Y %H:%M")
        status_icon = "✅" if cp.status == "accepted" else "❌"

        user_name = cp.user.display_name if cp.user else "?"
        obj_name = cp.object.name if cp.object else "?"

        text += (
            f"{i}. {status_icon} <b>{obj_name}</b>\n"
            f"   👤 {user_name}\n"
            f"   📏 {cp.distance_in_meters:.0f} m | 🕐 {time_str}\n\n"
        )

    return text
