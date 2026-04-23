"""
Checkpoint qilish jarayoni handleri.
"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from bot.config import get_settings
from bot.states.states import CheckpointStates
from bot.services.checkpoint_service import CheckpointService
from bot.services.notification_service import NotificationService
from bot.keyboards.user_kb import (
    objects_inline_kb,
    purpose_inline_kb,
    location_request_kb,
    retry_kb,
)
from bot.handlers.start import get_menu_kb

settings = get_settings()
router = Router(name="checkpoint")
checkpoint_service = CheckpointService()


@router.message(F.text == "📍 Checkpoint qilish")
async def start_checkpoint(message: Message, state: FSMContext):
    print(f"▶️ [DEBUG] Checkpoint button pressed. User: {message.from_user.id}")
    await state.clear()
    objects = checkpoint_service.get_all_objects()
    print(f"▶️ [DEBUG] Objects loaded from database: {len(objects) if objects else 0}")
    
    if objects is None:
        await message.answer("⚠️ Obyektlarni yuklashda xatolik yuz berdi.")
        return

    if not objects:
        await message.answer("😕 Hozircha hech qanday obyekt mavjud emas.")
        return

    await message.answer(
        "🏗 <b>Qaysi obyektga keldingiz?</b>\n\nObyektni tanlang:",
        reply_markup=objects_inline_kb(objects),
        parse_mode="HTML",
    )
    await state.set_state(CheckpointStates.selecting_object)


@router.callback_query(
    CheckpointStates.selecting_object,
    F.data.startswith("select_object:"),
)
async def object_selected(callback: CallbackQuery, state: FSMContext):
    object_id = int(callback.data.split(":")[1])
    obj = checkpoint_service.get_object_by_id(object_id)

    if not obj:
        await callback.answer("❌ Obyekt topilmadi!", show_alert=True)
        await state.clear()
        return

    print(f"▶️ [DEBUG] Selected object: ID={object_id}, Name={obj['name']}")
    await state.update_data(object_id=object_id, object_name=obj["name"])
    
    await callback.message.edit_text(
        f"✅ Tanlangan obyekt: <b>{obj['name']}</b>\n\n"
        "❓ Nima qilishga keldingiz?",
        parse_mode="HTML",
        reply_markup=purpose_inline_kb()
    )
    await state.set_state(CheckpointStates.waiting_purpose)
    await callback.answer()


@router.callback_query(
    CheckpointStates.waiting_purpose,
    F.data.startswith("purpose:"),
)
async def purpose_selected(callback: CallbackQuery, state: FSMContext):
    raw_purpose = callback.data.split(":")[1]
    purpose = "Pelesos qilishga" if raw_purpose == "pelesos" else "Promifka qilishga"
    print(f"▶️ [DEBUG] Selected purpose: {purpose}")

    await state.update_data(purpose=purpose)

    await callback.message.edit_text(
        f"✅ Maqsad: <b>{purpose}</b>\n\n"
        "📍 Endi joylashuvingizni yuboring:",
        parse_mode="HTML",
    )
    await callback.message.answer(
        "📍 Quyidagi tugmani bosing:",
        reply_markup=location_request_kb(),
    )
    await state.set_state(CheckpointStates.waiting_location)
    await callback.answer()


@router.message(CheckpointStates.waiting_location, F.location)
async def location_received(message: Message, state: FSMContext):
    user_lat = message.location.latitude
    user_lon = message.location.longitude
    print(f"▶️ [DEBUG] Location received: {user_lat}, {user_lon}")

    await state.update_data(
        user_lat=user_lat,
        user_lon=user_lon,
    )

    await message.answer(
        "📸 Iltimos, obyektda ekanligingizni tasdiqlash uchun rasm yuboring:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(CheckpointStates.waiting_photo)


@router.message(CheckpointStates.waiting_photo, F.photo)
async def photo_received(message: Message, state: FSMContext, bot: Bot):
    photo_id = message.photo[-1].file_id
    print(f"▶️ [DEBUG] Photo received. ID length: {len(photo_id)}")

    data = await state.get_data()
    object_id = data.get("object_id")
    purpose = data.get("purpose", "Noma'lum")
    user_lat = data.get("user_lat")
    user_lon = data.get("user_lon")

    if not object_id or not user_lat or not user_lon:
        await message.answer(
            "❌ Xatolik. Qaytadan boshlang.",
            reply_markup=get_menu_kb(message.from_user.id),
        )
        await state.clear()
        return

    notification_service = NotificationService(bot)
    obj = checkpoint_service.get_object_by_id(object_id)
    if not obj:
        await message.answer("❌ Obyekt topilmadi!", reply_markup=get_menu_kb(message.from_user.id))
        await state.clear()
        return

    full_name = message.from_user.first_name or ""
    if message.from_user.last_name:
        full_name += f" {message.from_user.last_name}"
    username = f"@{message.from_user.username}" if message.from_user.username else full_name.strip()

    distance, is_accepted = checkpoint_service.verify_location(user_lat, user_lon, obj)
    status = "Keldi" if is_accepted else "Kelmadi"
    print(f"▶️ [DEBUG] Distance calculated: {distance:.2f} m. Status: {status}")

    checkpoint = checkpoint_service.save_checkpoint(
        user_id=message.from_user.id,
        username=username,
        object_name=obj["name"],
        user_latitude=user_lat,
        user_longitude=user_lon,
        status=status,
        purpose=purpose,
    )
    
    if not checkpoint or not checkpoint.get("created_at"):
        print("❌ [DEBUG] CHECKPOINT INSERT error")
        await message.answer("❌ Checkpointni saqlashda xatolik yuz berdi.", reply_markup=get_menu_kb(message.from_user.id))
        await state.clear()
        return

    print("✅ [DEBUG] CHECKPOINT INSERT success")

    menu_kb = get_menu_kb(message.from_user.id)

    if is_accepted:
        await message.answer(
            "✅ <b>Checkpoint qabul qilindi!</b>\n\n"
            f"🏗 Obyekt: {obj['name']}\n"
            f"🛠 Maqsad: {purpose}\n"
            f"📏 Masofa: {distance:.0f} m\n"
            f"📍 Koordinata: {user_lat:.6f}, {user_lon:.6f}",
            parse_mode="HTML",
            reply_markup=menu_kb,
        )
    else:
        await message.answer(
            "❌ <b>Siz manzilga kelmadingiz!</b>\n\n"
            f"🏗 Obyekt: {obj['name']}\n"
            f"🛠 Maqsad: {purpose}\n"
            f"📏 Sizning masofangiz: {distance:.0f} m\n"
            f"📏 Ruxsat etilgan: {obj.get('radius', 500)} m\n\n"
            "Obyektga yaqinroq borib qayta urinib ko'ring.",
            parse_mode="HTML",
            reply_markup=menu_kb,
        )
        await message.answer("🔄 Qayta urinasizmi?", reply_markup=retry_kb())

    await notification_service.notify_checkpoint(checkpoint, is_accepted, photo_id)
    await state.clear()


@router.message(CheckpointStates.waiting_photo)
async def invalid_photo(message: Message):
    await message.answer("⚠️ Iltimos, faqat rasm yuboring!")


@router.callback_query(F.data == "retry_checkpoint")
async def retry_checkpoint(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    objects = checkpoint_service.get_all_objects()

    if objects is None:
        await callback.message.edit_text("⚠️ Obyektlarni yuklashda xatolik yuz berdi.")
        return

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
