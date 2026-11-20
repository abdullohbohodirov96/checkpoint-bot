"""
Jarimalar: admin va ishchi ko'rinishlari, boshlanish sanasini kiritish,
jarimani bekor qilish va ishchiga biriktirish.
"""

import html
from datetime import date, datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.config import get_settings
from bot.states.states import FineStates
from bot.keyboards.admin_kb import (
    fines_menu_kb,
    object_fine_settings_kb,
    period_days_kb,
    start_date_kb,
    start_dates_list_kb,
)
from bot.services.fine_service import FineService, now_local, parse_date
from bot.services.fine_scheduler import (
    MONTHS,
    admin_report_text,
    fine_reasons,
    fmt,
    fmt_period,
    money,
    rules_text,
    safe_send,
    send_long,
)

settings = get_settings()
router = Router(name="fines")

NOT_READY = "⚠️ Jarima tizimi hali sozlanmagan. Admin bilan bog'laning."


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids_list


def _service():
    try:
        svc = FineService()
        return svc if svc.schema_ok() else None
    except Exception as e:
        print(f"❌ [FINES] Servis xatosi: {e}")
        return None


# ──────────────────────────────────────────
# ISHCHI — O'Z JARIMALARI
# ──────────────────────────────────────────

@router.message(F.text == "💰 Jarimalarim")
async def my_fines(message: Message, state: FSMContext):
    await state.clear()
    svc = _service()
    if not svc:
        await message.answer(NOT_READY)
        return

    today = now_local().date()
    fines = svc.month_fines(today.year, today.month, user_id=message.from_user.id)
    text = f"💰 <b>Jarimalarim — {MONTHS[today.month - 1]} {today.year}</b>\n\n"
    if fines:
        reasons = await fine_reasons(svc, fines, today)
        for f in fines:
            text += f"🏗 <b>{html.escape(f['object_name'])}</b> — {money(f['amount'])}\n"
            text += (
                reasons.get(f["id"])
                or f"❌ {fmt_period(parse_date(f['period_start']), parse_date(f['period_end']))} — checkpoint qilinmadi."
            ) + "\n\n"
        total = sum(float(f["amount"]) for f in fines)
        text += f"Jami: {len(fines)} ta, <b>{money(total)}</b>\n\n"
    else:
        text += "Bu oy jarimangiz yo'q ✅\n\n"
    text += rules_text()
    await send_long(message.bot, message.chat.id, text)


# ──────────────────────────────────────────
# ADMIN — JARIMALAR
# ──────────────────────────────────────────

@router.message(F.text == "💰 Jarimalar")
async def admin_fines(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    svc = _service()
    if not svc:
        await message.answer(
            "⚠️ Jarima tizimi hali yoqilmagan: Supabase SQL Editor'da "
            "<code>migrations/2026_11_fines.sql</code> ni bir marta ishga tushiring.",
            parse_mode="HTML",
        )
        return

    today = now_local().date()
    fines = svc.month_fines(today.year, today.month)
    reasons = await fine_reasons(svc, fines, today)
    text = admin_report_text(fines, today, reasons).replace("Jarimalar hisoboti", "Joriy oy jarimalari")
    missing = [o["name"] for o in svc.objects() if not o.get("start_date")]
    if missing:
        text += (
            f"\n\n❓ Boshlanish sanasi kiritilmagan obyektlar: {len(missing)} ta "
            "— ular bo'yicha jarima hisoblanmayapti."
        )
    await send_long(message.bot, message.chat.id, text)
    await message.answer("⚙️ Sozlash:", reply_markup=fines_menu_kb())


# ──────────────────────────────────────────
# ADMIN — BOSHLANISH SANASI
# ──────────────────────────────────────────

@router.callback_query(F.data == "fstart:list")
async def start_dates_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return
    svc = _service()
    if not svc:
        await callback.answer(NOT_READY, show_alert=True)
        return
    objects = svc.objects()
    if not objects:
        await callback.answer("Obyektlar yo'q", show_alert=True)
        return
    await callback.message.answer(
        "🗓 <b>Obyektlar: boshlanish sanasi va muddat</b>\n\nO'zgartirish uchun obyektni tanlang:",
        parse_mode="HTML",
        reply_markup=start_dates_list_kb(objects[:90], svc.object_settings()[0], settings.FINE_PERIOD_DAYS),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fstart:pick:"))
async def start_date_pick(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return
    svc = _service()
    obj = svc.get_object(int(callback.data.split(":")[2])) if svc else None
    if not obj:
        await callback.answer("❌ Obyekt topilmadi!", show_alert=True)
        return
    current = parse_date(obj.get("start_date"))
    own_days = svc.object_settings()[0].get(obj["id"])
    await callback.message.answer(
        f"🏗 <b>{html.escape(obj['name'])}</b>\n"
        f"🗓 Boshlanish sanasi: <b>{fmt(current) if current else 'kiritilmagan'}</b>\n"
        f"⏱ Muddat: <b>{own_days or settings.FINE_PERIOD_DAYS} kun</b>"
        f"{'' if own_days else ' (standart)'} — shuncha kunda kamida 1 marta checkpoint",
        parse_mode="HTML",
        reply_markup=object_fine_settings_kb(obj["id"]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fstart:dates:"))
async def start_date_options(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return
    svc = _service()
    obj = svc.get_object(int(callback.data.split(":")[2])) if svc else None
    if not obj:
        await callback.answer("❌ Obyekt topilmadi!", show_alert=True)
        return
    await callback.message.answer(
        f"🗓 <b>{html.escape(obj['name'])}</b> — yangi boshlanish sanasini tanlang:",
        parse_mode="HTML",
        reply_markup=start_date_kb(obj["id"], parse_date(obj.get("created_at")), svc.first_checkpoint_date(obj["name"])),
    )
    await callback.answer()


# ──────────────────────────────────────────
# ADMIN — OBYEKT MUDDATI (KUN)
# ──────────────────────────────────────────

MAX_PERIOD_DAYS = 90


async def _save_period_days(svc: FineService, object_id: int, days: int) -> str:
    obj = svc.get_object(object_id)
    if not obj:
        return "❌ Obyekt topilmadi!"
    today = now_local().date()
    svc.set_period_days(object_id, days or None, today)
    shown = days or settings.FINE_PERIOD_DAYS
    return (
        f"✅ <b>{html.escape(obj['name'])}</b> — muddat: <b>{shown} kun</b>{'' if days else ' (standart)'}\n"
        f"Endi bu obyektda har {shown} kunda kamida 1 marta checkpoint bo'lishi kerak. "
        f"Hisob bugundan ({fmt(today)}) qaytadan boshlanadi."
    )


@router.callback_query(F.data.startswith("flimit:ask:"))
async def period_days_ask(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return
    object_id = int(callback.data.split(":")[2])
    await callback.message.answer(
        "⏱ Bu obyektda necha kunda kamida 1 marta checkpoint bo'lishi kerak?",
        reply_markup=period_days_kb(object_id, settings.FINE_PERIOD_DAYS),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("flimit:set:"))
async def period_days_set(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return
    svc = _service()
    if not svc:
        await callback.answer(NOT_READY, show_alert=True)
        return
    _, _, object_id, days = callback.data.split(":")
    await callback.message.edit_text(await _save_period_days(svc, int(object_id), int(days)), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("flimit:custom:"))
async def period_days_custom(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(FineStates.entering_period_days)
    await state.update_data(fine_object_id=int(callback.data.split(":")[2]))
    await callback.message.answer(f"✍️ Kunlar sonini kiriting (1–{MAX_PERIOD_DAYS}). Masalan: <code>10</code>", parse_mode="HTML")
    await callback.answer()


@router.message(FineStates.entering_period_days)
async def period_days_entered(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    raw = (message.text or "").strip()
    if not raw.isdigit() or not 1 <= int(raw) <= MAX_PERIOD_DAYS:
        await message.answer(
            f"❌ 1 dan {MAX_PERIOD_DAYS} gacha son kiriting. Bekor qilish uchun /start bosing."
        )
        return
    data = await state.get_data()
    await state.clear()
    svc = _service()
    if not svc or not data.get("fine_object_id"):
        await message.answer(NOT_READY)
        return
    await message.answer(await _save_period_days(svc, data["fine_object_id"], int(raw)), parse_mode="HTML")


async def _save_start_date(svc: FineService, object_id: int, start: date) -> str:
    obj = svc.get_object(object_id)
    if not obj:
        return "❌ Obyekt topilmadi!"
    svc.set_start_date(object_id, start)
    return (
        f"✅ <b>{html.escape(obj['name'])}</b> — boshlanish sanasi: <b>{fmt(start)}</b>\n"
        "Checkpoint muddati hisobi shu kundan yuradi."
    )


@router.callback_query(F.data.startswith("fstart:today:"))
async def start_date_today(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return
    svc = _service()
    if not svc:
        await callback.answer(NOT_READY, show_alert=True)
        return
    text = await _save_start_date(svc, int(callback.data.split(":")[2]), now_local().date())
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("fstart:set:"))
async def start_date_set(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return
    svc = _service()
    if not svc:
        await callback.answer(NOT_READY, show_alert=True)
        return
    _, _, object_id, raw = callback.data.split(":")
    start = datetime.strptime(raw, "%Y%m%d").date()
    text = await _save_start_date(svc, int(object_id), start)
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("fstart:custom:"))
async def start_date_custom(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(FineStates.entering_start_date)
    await state.update_data(fine_object_id=int(callback.data.split(":")[2]))
    await callback.message.answer(
        "✍️ Sanani kiriting (kun.oy.yil).\nMasalan: <code>15.11.2026</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(FineStates.entering_start_date)
async def start_date_entered(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    raw = (message.text or "").strip().replace("/", ".").replace("-", ".")
    try:
        start = datetime.strptime(raw, "%d.%m.%Y").date()
    except ValueError:
        await message.answer(
            "❌ Sana noto'g'ri. Format: <code>15.11.2026</code>\nBekor qilish uchun /start bosing.",
            parse_mode="HTML",
        )
        return
    data = await state.get_data()
    await state.clear()
    svc = _service()
    if not svc or not data.get("fine_object_id"):
        await message.answer(NOT_READY)
        return
    await message.answer(await _save_start_date(svc, data["fine_object_id"], start), parse_mode="HTML")


# ──────────────────────────────────────────
# ADMIN — JARIMANI BEKOR QILISH / BIRIKTIRISH
# ──────────────────────────────────────────

@router.callback_query(F.data.startswith("fine:cancel:"))
async def fine_cancel(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return
    svc = _service()
    fine = svc.get_fine(int(callback.data.split(":")[2])) if svc else None
    if not fine:
        await callback.answer("❌ Jarima topilmadi!", show_alert=True)
        return
    if fine.get("status") == "cancelled":
        await callback.answer("Bu jarima allaqachon bekor qilingan.", show_alert=True)
        return
    svc.cancel_fine(fine["id"])
    period = fmt_period(parse_date(fine["period_start"]), parse_date(fine["period_end"]))
    name = html.escape(fine["object_name"])
    await callback.message.edit_text(
        f"🚫 <b>Jarima bekor qilindi</b>\n\n🏗 {name} ({period}) — {money(fine['amount'])}\n"
        f"👤 {html.escape(fine.get('username') or 'belgilanmagan')}",
        parse_mode="HTML",
    )
    if fine.get("user_id"):
        await safe_send(
            bot, fine["user_id"],
            f"✅ <b>{name}</b> obyekti ({period}) bo'yicha {money(fine['amount'])} jarimangiz admin tomonidan bekor qilindi.",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("fine:assign:"))
async def fine_assign(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return
    _, _, fine_id, user_id = callback.data.split(":")
    svc = _service()
    fine = svc.get_fine(int(fine_id)) if svc else None
    if not fine or fine.get("status") != "active":
        await callback.answer("❌ Jarima topilmadi yoki bekor qilingan!", show_alert=True)
        return
    if fine.get("user_id"):
        await callback.answer("Bu jarima allaqachon ishchiga yozilgan.", show_alert=True)
        return
    user_id = int(user_id)
    username = svc.known_workers().get(user_id, str(user_id))
    svc.assign_fine(fine["id"], user_id, username)

    period = fmt_period(parse_date(fine["period_start"]), parse_date(fine["period_end"]))
    name = html.escape(fine["object_name"])
    from bot.keyboards.admin_kb import fine_admin_kb
    await callback.message.edit_text(
        f"💸 <b>Jarima yozildi</b>\n\n🏗 {name} ({period}) — {money(fine['amount'])}\n"
        f"👤 Ishchi: {html.escape(username)}",
        parse_mode="HTML",
        reply_markup=fine_admin_kb(fine["id"]),
    )
    await safe_send(
        bot, user_id,
        "💸 <b>Sizga jarima yozildi</b>\n\n"
        f"🏗 Obyekt: <b>{name}</b>\n"
        f"📅 Davr: {period}\n"
        "❌ Bu davr ichida obyektda bir marta ham checkpoint qilinmadi.\n"
        f"💰 Jarima: <b>{money(fine['amount'])}</b>\n\n"
        f"Savol bo'lsa admin: @{settings.FINE_ADMIN_USERNAME}",
    )
    await callback.answer()
