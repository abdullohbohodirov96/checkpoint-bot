"""
Jarima tizimining fon vazifasi: boshlanish sanasini so'rash, jarima yozish,
eslatma, oylik hisobot va ishga tushgandagi e'lon.
"""

import asyncio
import calendar
import html
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from aiogram import Bot

from bot.config import get_settings
from bot.keyboards.admin_kb import fine_admin_kb, start_date_kb
from bot.services.fine_service import (
    LAUNCH_KEY,
    FineService,
    current_period,
    due_periods,
    now_local,
    parse_date,
)

settings = get_settings()
logger = logging.getLogger(__name__)

TICK_SECONDS = 30 * 60
# Xabarlar faqat shu soatlar oralig'ida yuboriladi (Toshkent vaqti)
DAY_START_HOUR = 9
DAY_END_HOUR = 21
REPORT_HOUR = 18
# Javob bo'lmasa boshlanish sanasi necha soatdan keyin qayta so'raladi
ASK_AGAIN_HOURS = 24

MONTHS = [
    "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
]


def fmt(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def fmt_period(ps: date, pe: date) -> str:
    """Davrni oxirgi kuni bilan ko'rsatadi (pe o'zi davrga kirmaydi)."""
    return f"{ps.strftime('%d.%m')}–{(pe - timedelta(days=1)).strftime('%d.%m.%Y')}"


def money(amount: Any) -> str:
    try:
        return f"{int(float(amount))}$"
    except (TypeError, ValueError):
        return f"{amount}$"


def rules_text() -> str:
    n = settings.FINE_PERIOD_DAYS
    return (
        "📌 <b>Qoida:</b>\n"
        f"• Har bir obyektda <b>har {n} kunda kamida 1 marta</b> checkpoint qilinishi shart "
        "(ayrim obyektlarga admin boshqa muddat belgilashi mumkin).\n"
        "• Hisob obyekt ochilgan kundan boshlab yuradi.\n"
        "• Obyektda muddat ichida bir marta ham qabul qilingan (✅) checkpoint bo'lmasa — "
        f"shu obyektga mas'ul ishchiga <b>{settings.FINE_AMOUNT}$ jarima</b> yoziladi.\n"
        "• Qoida <b>barcha obyektlar</b> uchun amal qiladi.\n"
        "• Faqat joyida qilingan (✅ qabul qilingan) checkpoint hisobga olinadi.\n\n"
        "👤 Mas'ul ishchi — obyektda oxirgi marta checkpoint qilgan ishchi.\n"
        f"⏰ Muddat tugashiga {settings.FINE_WARN_DAYS} kun qolganda (standart muddatda — "
        f"{n - settings.FINE_WARN_DAYS} kun o'tganda) bot eslatma yuboradi.\n"
        "📊 Har oyning oxirgi kuni jarimalar hisoboti admin va ishchilarga yuboriladi.\n"
        "💰 Jarimalaringizni «💰 Jarimalarim» tugmasi orqali ko'rishingiz mumkin."
    )


def announcement_text() -> str:
    return (
        "📢 <b>Muhim e'lon — yangi qoida!</b>\n\n"
        "Bugundan boshlab checkpoint bo'yicha <b>jarima tizimi</b> ishga tushdi.\n\n"
        f"{rules_text()}\n\n"
        "ℹ️ Avvaldan bor obyektlar uchun hisob bugundan boshlanadi — o'tgan kunlar uchun jarima yozilmaydi.\n\n"
        f"❓ Savollar bo'yicha admin: @{settings.FINE_ADMIN_USERNAME}"
    )


async def db(fn, *args):
    """Supabase so'rovlari sinxron — botni to'xtatib qo'ymaslik uchun alohida oqimda bajaramiz."""
    return await asyncio.to_thread(fn, *args)


def reason_text(fine: Dict[str, Any], ctx: Dict[str, Any], today: date) -> str:
    """Jarima sababi: qaysi davrda borilmagan, oxirgi va keyingi checkpoint qachon bo'lgan."""
    ps, pe = parse_date(fine["period_start"]), parse_date(fine["period_end"])
    n = (pe - ps).days
    last, nxt = ctx.get("last"), ctx.get("next")
    lines = [f"❌ {fmt_period(ps, pe)} — {n} kun ichida bir marta ham checkpoint qilinmadi."]
    if last:
        lines.append(f"🕒 Bundan oldingi oxirgi checkpoint: {fmt(last)}")
    else:
        lines.append("🕒 Bundan oldin bu obyektda umuman checkpoint bo'lmagan.")
    since = last or ps
    if nxt:
        who = f" ({html.escape(ctx['next_user'])})" if ctx.get("next_user") else ""
        lines.append(
            f"✅ Keyin {fmt(nxt)} da borilgan{who} — orada {(nxt - since).days} kun o'tgan (ruxsat etilgani {n} kun)."
        )
    else:
        lines.append(f"⏳ Shu kungacha hali borilmagan — {(today - since).days} kun bo'ldi (ruxsat etilgani {n} kun).")
    return "\n".join(lines)


async def fine_reasons(svc: FineService, fines: List[Dict[str, Any]], today: date) -> Dict[Any, str]:
    reasons: Dict[Any, str] = {}
    for f in fines:
        try:
            ctx = await db(
                svc.fine_context, f["object_name"], parse_date(f["period_start"]), parse_date(f["period_end"])
            )
            reasons[f["id"]] = reason_text(f, ctx, today)
        except Exception as e:
            logger.warning(f"[FINES] Sabab hisoblanmadi (jarima {f.get('id')}): {e}")
    return reasons


def _indent(text: str, pad: str = "     ") -> str:
    return "\n".join(pad + line for line in text.split("\n"))


async def safe_send(bot: Bot, chat_id: int, text: str, **kwargs) -> bool:
    try:
        await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        return True
    except Exception as e:
        logger.warning(f"[FINES] {chat_id} ga xabar yuborilmadi: {e}")
        return False


async def send_long(bot: Bot, chat_id: int, text: str) -> bool:
    """4096 belgidan uzun matnni qatorlar bo'yicha bo'lib yuboradi."""
    ok = True
    chunk = ""
    for line in text.split("\n"):
        if len(chunk) + len(line) + 1 > 3800:
            ok = await safe_send(bot, chat_id, chunk) and ok
            chunk = ""
        chunk += line + "\n"
    if chunk.strip():
        ok = await safe_send(bot, chat_id, chunk) and ok
    return ok


# ──────────────────────────────────────────
# E'LON
# ──────────────────────────────────────────

async def announce_launch(bot: Bot, svc: FineService) -> None:
    from bot.handlers.start import get_menu_kb

    text = announcement_text()
    recipients = set(await db(svc.known_workers)) | set(settings.admin_ids_list)
    sent = 0
    for uid in recipients:
        # Menyu ham yangilanadi — «💰 Jarimalarim» tugmasi paydo bo'ladi
        if await safe_send(bot, uid, text, reply_markup=get_menu_kb(uid)):
            sent += 1
        await asyncio.sleep(0.05)
    if settings.CHANNEL_ID:
        await safe_send(bot, settings.CHANNEL_ID, text)
    logger.info(f"[FINES] E'lon yuborildi: {sent}/{len(recipients)}")


# ──────────────────────────────────────────
# BOSHLANISH SANASINI SO'RASH
# ──────────────────────────────────────────

async def ask_start_date(bot: Bot, svc: FineService, obj: Dict[str, Any]) -> bool:
    created = None
    if obj.get("created_at"):
        try:
            created = datetime.fromisoformat(str(obj["created_at"]).replace("Z", "+00:00")).date()
        except ValueError:
            created = None
    first = await db(svc.first_checkpoint_date, obj["name"])
    text = (
        f"🗓 <b>{html.escape(obj['name'])}</b> obyekti qaysi kundan boshlangan?\n\n"
        "Jarima hisobi shu kundan yuradi. "
        "Sana kiritilmaguncha bu obyekt bo'yicha jarima hisoblanmaydi."
    )
    return await safe_send(
        bot, settings.FINE_ADMIN_ID, text,
        reply_markup=start_date_kb(obj["id"], created, first),
    )


async def ask_missing_start_dates(bot: Bot, svc: FineService) -> None:
    now_utc = datetime.now(timezone.utc)
    for obj in await db(svc.objects):
        if obj.get("start_date"):
            continue
        asked = obj.get("start_asked_at")
        if asked:
            try:
                asked_dt = datetime.fromisoformat(str(asked).replace("Z", "+00:00"))
                if now_utc - asked_dt < timedelta(hours=ASK_AGAIN_HOURS):
                    continue
            except ValueError:
                pass
        if await ask_start_date(bot, svc, obj):
            await db(svc.mark_asked, obj["id"])
        await asyncio.sleep(0.05)


# ──────────────────────────────────────────
# JARIMA YOZISH
# ──────────────────────────────────────────

async def notify_fine(bot: Bot, svc: FineService, fine: Dict[str, Any], today: date) -> None:
    ps, pe = parse_date(fine["period_start"]), parse_date(fine["period_end"])
    name = html.escape(fine["object_name"])
    period = fmt_period(ps, pe)
    amount = money(fine["amount"])
    reason = (await fine_reasons(svc, [fine], today)).get(fine["id"]) or (
        f"❌ {period} — {(pe - ps).days} kun ichida bir marta ham checkpoint qilinmadi."
    )

    if fine.get("user_id"):
        await safe_send(
            bot, fine["user_id"],
            "💸 <b>Sizga jarima yozildi</b>\n\n"
            f"🏗 Obyekt: <b>{name}</b>\n"
            f"💰 Jarima: <b>{amount}</b>\n\n"
            f"<b>Sababi:</b>\n{reason}\n\n"
            f"Savol bo'lsa admin: @{settings.FINE_ADMIN_USERNAME}",
        )
        who = f"👤 Ishchi: {html.escape(fine.get('username') or str(fine['user_id']))}"
        workers = None
    else:
        who = "👤 Ishchi: <b>belgilanmagan</b> — bu obyektda hali hech kim checkpoint qilmagan.\nKimga yozilsin? Pastdan tanlang:"
        workers = await db(svc.known_workers)

    await safe_send(
        bot, settings.FINE_ADMIN_ID,
        "💸 <b>Yangi jarima</b>\n\n"
        f"🏗 Obyekt: <b>{name}</b>\n"
        f"💰 Jarima: <b>{amount}</b>\n"
        f"{who}\n\n"
        f"<b>Sababi:</b>\n{reason}",
        reply_markup=fine_admin_kb(fine["id"], workers),
    )


async def process_fines(bot: Bot, svc: FineService, launch: date, today: date) -> int:
    created = 0
    days_by_obj, anchors = await db(svc.object_settings)
    for obj in await db(svc.objects):
        start = parse_date(obj.get("start_date"))
        if not start:
            continue
        try:
            periods = due_periods(
                start,
                max(launch, anchors.get(obj["id"], launch)),
                parse_date(obj.get("fine_checked_until")),
                today,
                days_by_obj.get(obj["id"]) or settings.FINE_PERIOD_DAYS,
            )
            for ps, pe in periods:
                if not await db(svc.has_checkpoint, obj["name"], ps, pe) and not await db(svc.fine_exists, obj["id"], ps):
                    fine = await db(svc.create_fine, obj, ps, pe, await db(svc.last_worker, obj["name"]), settings.FINE_AMOUNT)
                    await db(svc.set_checked_until, obj["id"], pe)
                    created += 1
                    await notify_fine(bot, svc, fine, today)
                else:
                    await db(svc.set_checked_until, obj["id"], pe)
        except Exception as e:
            # Keyingi tekshiruvda qayta uriniladi
            logger.error(f"[FINES] {obj.get('name')} bo'yicha xato: {e}")
    return created


# ──────────────────────────────────────────
# ESLATMA
# ──────────────────────────────────────────

async def send_warnings(bot: Bot, svc: FineService, launch: date, today: date) -> None:
    days_by_obj, anchors = await db(svc.object_settings)
    for obj in await db(svc.objects):
        start = parse_date(obj.get("start_date"))
        if not start:
            continue
        try:
            days = days_by_obj.get(obj["id"]) or settings.FINE_PERIOD_DAYS
            period = current_period(start, max(launch, anchors.get(obj["id"], launch)), today, days)
            if not period:
                continue
            ps, pe = period
            # Qisqa muddatli obyektda eslatma davr boshidayoq ketib qolmasin
            if (pe - today).days > min(settings.FINE_WARN_DAYS, days - 1):
                continue
            if parse_date(obj.get("fine_warned_period")) == ps:
                continue
            if await db(svc.has_checkpoint, obj["name"], ps, pe):
                continue
            worker = await db(svc.last_worker, obj["name"])
            if worker:
                last_day = pe - timedelta(days=1)
                await safe_send(
                    bot, worker[0],
                    "⚠️ <b>Eslatma</b>\n\n"
                    f"🏗 <b>{html.escape(obj['name'])}</b> obyektida bu {days} kunlik davrda "
                    f"({fmt_period(ps, pe)}) hali checkpoint yo'q.\n"
                    f"📅 Oxirgi kun: <b>{fmt(last_day)}</b>\n"
                    f"Shu kungacha checkpoint qilmasangiz <b>{settings.FINE_AMOUNT}$ jarima</b> yoziladi.",
                )
            await db(svc.set_warned, obj["id"], ps)
        except Exception as e:
            logger.error(f"[FINES] Eslatma xatosi ({obj.get('name')}): {e}")


# ──────────────────────────────────────────
# OYLIK HISOBOT
# ──────────────────────────────────────────

def report_target(today: date, hour: int) -> Optional[date]:
    """Hisobot yuborilishi kerak bo'lgan oyning oxirgi kuni (yoki None)."""
    last_day = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    if today == last_day and hour >= REPORT_HOUR:
        return last_day
    if today.day <= 5:
        # Oy oxirida bot ishlamay qolgan bo'lsa — o'tgan oy hisobotini yetkazib beramiz
        return today.replace(day=1) - timedelta(days=1)
    return None


def admin_report_text(
    fines: List[Dict[str, Any]], month_end: date, reasons: Optional[Dict[Any, str]] = None
) -> str:
    reasons = reasons or {}
    title = f"📊 <b>Jarimalar hisoboti — {MONTHS[month_end.month - 1]} {month_end.year}</b>\n\n"
    if not fines:
        return title + "Bu oy jarima yozilmadi ✅"
    by_worker: Dict[Any, List[Dict[str, Any]]] = {}
    for f in fines:
        by_worker.setdefault(f.get("user_id"), []).append(f)
    text = title
    total = 0.0
    for uid, items in sorted(by_worker.items(), key=lambda kv: -sum(float(i["amount"]) for i in kv[1])):
        subtotal = sum(float(i["amount"]) for i in items)
        total += subtotal
        who = html.escape(items[0].get("username") or str(uid)) if uid else "Ishchi belgilanmagan"
        text += f"👤 <b>{who}</b> — {len(items)} ta, <b>{money(subtotal)}</b>\n"
        for i in items:
            text += f"   • <b>{html.escape(i['object_name'])}</b> — {money(i['amount'])}\n"
            text += _indent(
                reasons.get(i["id"])
                or f"❌ {fmt_period(parse_date(i['period_start']), parse_date(i['period_end']))} — checkpoint qilinmadi."
            ) + "\n"
        text += "\n"
    text += f"Jami: {len(fines)} ta jarima, <b>{money(total)}</b>"
    return text


def worker_report_text(
    fines: List[Dict[str, Any]], month_end: date, reasons: Optional[Dict[Any, str]] = None
) -> str:
    reasons = reasons or {}
    title = f"📊 <b>{MONTHS[month_end.month - 1]} {month_end.year} — jarimalar hisoboti</b>\n\n"
    if not fines:
        return title + "Sizda bu oy jarima yo'q ✅ Rahmat!"
    text = title
    for i in fines:
        text += f"🏗 <b>{html.escape(i['object_name'])}</b> — {money(i['amount'])}\n"
        text += (
            reasons.get(i["id"])
            or f"❌ {fmt_period(parse_date(i['period_start']), parse_date(i['period_end']))} — checkpoint qilinmadi."
        ) + "\n\n"
    total = sum(float(i["amount"]) for i in fines)
    text += f"Jami: {len(fines)} ta jarima, <b>{money(total)}</b>\n"
    text += f"Savol bo'lsa admin: @{settings.FINE_ADMIN_USERNAME}"
    return text


async def monthly_report(bot: Bot, svc: FineService, launch: date, today: date, hour: int) -> bool:
    month_end = report_target(today, hour)
    if not month_end or month_end < launch:
        return False
    key = f"fines_report:{month_end.strftime('%Y-%m')}"
    if await db(svc.get_setting, key):
        return False

    # Avval hamma ma'lumotni yig'amiz — xato bo'lsa keyingi tekshiruvda qayta uriniladi
    fines = await db(svc.unreported_fines, month_end)
    reasons = await fine_reasons(svc, fines, today)
    workers = await db(svc.known_workers)
    await db(svc.set_setting, key, now_local().isoformat())

    admin_text = admin_report_text(fines, month_end, reasons)
    for admin_id in settings.admin_ids_list:
        await send_long(bot, admin_id, admin_text)

    by_worker: Dict[int, List[Dict[str, Any]]] = {}
    for f in fines:
        if f.get("user_id"):
            by_worker.setdefault(f["user_id"], []).append(f)
    for uid in set(workers) | set(by_worker):
        if uid in settings.admin_ids_list and uid not in by_worker:
            continue
        await send_long(bot, uid, worker_report_text(by_worker.get(uid, []), month_end, reasons))
        await asyncio.sleep(0.05)

    await db(svc.mark_reported, [f["id"] for f in fines])
    return True


# ──────────────────────────────────────────
# ASOSIY SIKL
# ──────────────────────────────────────────

_schema_warned = False


async def tick(bot: Bot, now: Optional[datetime] = None) -> bool:
    """Bir marta tekshiradi. Sxema tayyor bo'lmasa False qaytaradi."""
    global _schema_warned
    now = now or now_local()
    today = now.date()

    svc = await db(FineService)
    if not await db(svc.schema_ok):
        if not _schema_warned:
            _schema_warned = True
            for admin_id in settings.admin_ids_list:
                await safe_send(
                    bot, admin_id,
                    "⚠️ Jarima tizimi hali yoqilmadi: Supabase'da <code>migrations/2026_11_fines.sql</code> "
                    "ishga tushirilmagan. SQL Editor'da bir marta Run qiling — bot o'zi davom ettiradi.",
                )
        return False

    # Tunda hech kimga xabar yubormaymiz
    if not DAY_START_HOUR <= now.hour < DAY_END_HOUR:
        return True

    launch = await db(svc.launch_date)
    if not launch:
        launch = today
        await db(svc.set_setting, LAUNCH_KEY, today.isoformat())
        await announce_launch(bot, svc)

    await ask_missing_start_dates(bot, svc)
    await process_fines(bot, svc, launch, today)
    await send_warnings(bot, svc, launch, today)
    await monthly_report(bot, svc, launch, today, now.hour)
    return True


async def fines_loop(bot: Bot) -> None:
    await asyncio.sleep(5)
    while True:
        ready = False
        try:
            ready = await tick(bot)
        except Exception as e:
            logger.error(f"[FINES] Tekshiruvda xato: {e}")
        # Migratsiya kutilayotgan bo'lsa tez-tez tekshiramiz
        await asyncio.sleep(TICK_SECONDS if ready else 120)
