"""
Checkpoint qilish jarayoni handleri.
1. Obyektni tanlash
2. Lokatsiya yuborish
3. Tekshirish va saqlash
"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.states.states import CheckpointStates
from bot.services.checkpoint_service import CheckpointService
from bot.services.user_service import UserService
from bot.services.notification_service import NotificationService
from bot.keyboards.user_kb import (
    objects_inline_kb,
    location_request_kb,
    retry_kb,
    main_menu_kb,
)
from bot.keyboards.admin_kb import admin_menu_kb
from bot.handlers.start import get_menu_kb

settings = get_settings()
router = Router(name="checkpoint")


# ──────────────────────────────────────────
# 1. CHECKPOINT BOSHLASH
# ──────────────────────────────────────────

@router.message(F.text == "📍 Checkpoint qilish")
async def start_checkpoint(message: Message, session: AsyncSession, state: FSMContext):
    """Obyektlar ro'yxatini ko'rsatish"""
    await state.clear()

    service = CheckpointService(session)
    objects = await service.get_all_objects()

    if not objects:
        await message.answer("😕 Hozircha hech qanday obyekt mavjud emas.")
        return

    await message.answer(
        "🏗 <b>Qaysi obyektga keldingiz?</b>\n\nObyektni tanlang:",
        reply_markup=objects_inline_kb(objects),
        parse_mode="HTML",
    )
    await state.set_state(CheckpointStates.selecting_object)


# ──────────────────────────────────────────
# 2. OBYEKT TANLANDI
# ──────────────────────────────────────────

@router.callback_query(
    CheckpointStates.selecting_object,
    F.data.startswith("select_object:"),
)
async def object_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Obyekt tanlandi — lokatsiya so'rash"""
    object_id = int(callback.data.split(":")[1])

    service = CheckpointService(session)
    obj = await service.get_object_by_id(object_id)

    if not obj:
        await callback.answer("❌ Obyekt topilmadi!", show_alert=True)
        await state.clear()
        return

    await state.update_data(object_id=object_id, object_name=obj.name)

    await callback.message.edit_text(
        f"✅ Tanlangan: <b>{obj.name}</b>\n\n"
        "📍 Endi joylashuvingizni yuboring:",
        parse_mode="HTML",
    )

    await callback.message.answer(
        "📍 Quyidagi tugmani bosing:",
        reply_markup=location_request_kb(),
    )

    await state.set_state(CheckpointStates.waiting_location)
    await callback.answer()


# ──────────────────────────────────────────
# 3. LOKATSIYA QABUL QILISH VA TEKSHIRISH
# ──────────────────────────────────────────

@router.message(CheckpointStates.waiting_location, F.location)
async def location_received(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Lokatsiya olindi — tekshirish"""
    data = await state.get_data()
    object_id = data.get("object_id")

    if not object_id:
        await message.answer(
            "❌ Xatolik. Qaytadan boshlang.",
            reply_markup=get_menu_kb(message.from_user.id),
        )
        await state.clear()
        return

    # Xizmatlar
    checkpoint_service = CheckpointService(session)
    user_service = UserService(session)
    notification_service = NotificationService(bot)

    # Obyektni olish
    obj = await checkpoint_service.get_object_by_id(object_id)
    if not obj:
        await message.answer("❌ Obyekt topilmadi!", reply_markup=get_menu_kb(message.from_user.id))
        await state.clear()
        return

    # Foydalanuvchini olish
    full_name = message.from_user.first_name or ""
    if message.from_user.last_name:
        full_name += f" {message.from_user.last_name}"

    user = await user_service.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=full_name.strip(),
    )

    # Masofani hisoblash
    user_lat = message.location.latitude
    user_lon = message.location.longitude
    distance, is_accepted = checkpoint_service.verify_location(user_lat, user_lon, obj)

    status = "accepted" if is_accepted else "rejected"

    # Checkpoint saqlash
    checkpoint = await checkpoint_service.save_checkpoint(
        user_id=user.id,
        object_id=obj.id,
        user_latitude=user_lat,
        user_longitude=user_lon,
        distance_in_meters=distance,
        status=status,
    )

    menu_kb = get_menu_kb(message.from_user.id)

    if is_accepted:
        # ✅ QABUL QILINDI
        await message.answer(
            "✅ <b>Checkpoint qabul qilindi!</b>\n\n"
            f"🏗 Obyekt: {obj.name}\n"
            f"📏 Masofa: {distance:.0f} m\n"
            f"📍 Koordinata: {user_lat:.6f}, {user_lon:.6f}",
            parse_mode="HTML",
            reply_markup=menu_kb,
        )
        # Admin ga xabar
        await notification_service.notify_checkpoint(user, obj, checkpoint)
    else:
        # ❌ RAD ETILDI
        await message.answer(
            "❌ <b>Siz manzilga kelmadingiz!</b>\n\n"
            f"🏗 Obyekt: {obj.name}\n"
            f"📏 Sizning masofangiz: {distance:.0f} m\n"
            f"📏 Ruxsat etilgan: {obj.radius} m\n\n"
            "Objektga yaqinroq borib qayta urinib ko'ring.",
            parse_mode="HTML",
            reply_markup=menu_kb,
        )
        await message.answer("🔄 Qayta urinasizmi?", reply_markup=retry_kb())

    await state.clear()


# ──────────────────────────────────────────
# QAYTA URINISH
# ──────────────────────────────────────────

@router.callback_query(F.data == "retry_checkpoint")
async def retry_checkpoint(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Qayta urinish"""
    await state.clear()

    service = CheckpointService(session)
    objects = await service.get_all_objects()

    if not objects:
        await callback.message.edit_text("😕 Hech qanday obyekt mavjud emas.")
        return

    await callback.message.edit_text(
        "🏗 <b>Qaysi obyektga keldingiz?</b>\n\nObyektni tanlang:",
        reply_markup=objects_inline_kb(objects),
        parse_mode="HTML",
    )
    await state.set_state(CheckpointStates.selecting_object)
    await callback.answer()


# ──────────────────────────────────────────
# BEKOR QILISH
# ──────────────────────────────────────────

@router.callback_query(F.data == "cancel_checkpoint")
async def cancel_checkpoint(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.message.answer(
        "🏠 Bosh menyu:",
        reply_markup=get_menu_kb(callback.from_user.id),
    )
    await callback.answer()


@router.callback_query(F.data == "go_main_menu")
async def go_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🏠 Bosh menyu")
    await callback.message.answer(
        "Tugmani tanlang:",
        reply_markup=get_menu_kb(callback.from_user.id),
    )
    await callback.answer()


# ──────────────────────────────────────────
# NOTO'G'RI INPUT
# ──────────────────────────────────────────

@router.message(CheckpointStates.waiting_location, F.text == "❌ Bekor qilish")
async def cancel_location(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Bekor qilindi.",
        reply_markup=get_menu_kb(message.from_user.id),
    )


@router.message(CheckpointStates.waiting_location)
async def invalid_location(message: Message):
    await message.answer(
        "⚠️ Iltimos, joylashuvingizni yuboring!\n"
        "📍 Quyidagi tugmani bosing.",
        reply_markup=location_request_kb(),
    )
