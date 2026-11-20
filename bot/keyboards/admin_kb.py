"""
Admin uchun Telegram klaviaturalari.
Doimiy reply keyboard tugmalar — inline panel o'rniga.
"""

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from datetime import date
from typing import List, Dict, Any, Optional


# ──────────────────────────────────────────────────
# ADMIN DOIMIY MENYUSI (Reply Keyboard)
# ──────────────────────────────────────────────────

def admin_menu_kb() -> ReplyKeyboardMarkup:
    """
    Admin uchun doimiy menyu.
    """
    keyboard = [
        [KeyboardButton(text="📍 Checkpoint qilish")],
        [KeyboardButton(text="📋 Tarix")],
        [KeyboardButton(text="🏗 Obyektlar ro'yxati")],
        [
            KeyboardButton(text="➕ Manzil qo'shish"),
            KeyboardButton(text="🗑 Manzilni o'chirish"),
        ],
        [KeyboardButton(text="📋 Checkpointlar tarixi")],
        [KeyboardButton(text="💰 Jarimalar")],
        [KeyboardButton(text="❓ Yordam")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Admin menyu...",
    )


# ──────────────────────────────────────────────────
# ADMIN — OBYEKT TANLASH (O'chirish uchun)
# ──────────────────────────────────────────────────

def admin_objects_delete_kb(objects: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """O'chirish uchun obyektlar ro'yxati"""
    buttons = []
    for obj in objects:
        buttons.append([
            InlineKeyboardButton(
                text=f"🏗 {obj.get('name', '?')} (r={obj.get('radius', 500)}m)",
                callback_data=f"admin:delete_confirm:{obj.get('id', 0)}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="go_main_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ──────────────────────────────────────────────────
# O'CHIRISHNI TASDIQLASH
# ──────────────────────────────────────────────────

def confirm_delete_kb(object_id: int) -> InlineKeyboardMarkup:
    """O'chirishni tasdiqlash"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"admin:do_delete:{object_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="go_main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ──────────────────────────────────────────────────
# ADMIN TARIX MODE TANLASH (Location / General)
# ──────────────────────────────────────────────────

def admin_history_mode_kb() -> InlineKeyboardMarkup:
    """Admin tarix rejimini tanlash"""
    buttons = [
        [InlineKeyboardButton(text="📍 Location bo'yicha", callback_data="admin:history_mode:location")],
        [InlineKeyboardButton(text="🌐 General", callback_data="admin:history_mode:general")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="go_main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ──────────────────────────────────────────────────
# ADMIN TARIX — MANZIL TANLASH
# ──────────────────────────────────────────────────

def admin_history_objects_kb(objects: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Admin tarix uchun manzil tanlash"""
    buttons = []
    for obj in objects:
        buttons.append([
            InlineKeyboardButton(
                text=f"🏗 {obj.get('name', '?')}",
                callback_data=f"admin:history_obj:{obj.get('name', '?')}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:history_back"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ──────────────────────────────────────────────────
# ADMIN TARIX SAHIFALASH
# ──────────────────────────────────────────────────

def admin_history_pagination_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Admin tarix sahifalash"""
    buttons = []
    nav = []

    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin:history_page:{page - 1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin:history_page:{page + 1}"))

    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ──────────────────────────────────────────────────
# JARIMALAR
# ──────────────────────────────────────────────────

def start_date_kb(object_id: int, created: Optional[date], first_checkpoint: Optional[date]) -> InlineKeyboardMarkup:
    """Obyekt boshlanish sanasini tanlash"""
    buttons = [[InlineKeyboardButton(text="📅 Bugundan", callback_data=f"fstart:today:{object_id}")]]
    if created:
        buttons.append([InlineKeyboardButton(
            text=f"🗓 Qo'shilgan kundan ({created.strftime('%d.%m.%Y')})",
            callback_data=f"fstart:set:{object_id}:{created.strftime('%Y%m%d')}",
        )])
    if first_checkpoint and first_checkpoint != created:
        buttons.append([InlineKeyboardButton(
            text=f"📍 Birinchi checkpoint kunidan ({first_checkpoint.strftime('%d.%m.%Y')})",
            callback_data=f"fstart:set:{object_id}:{first_checkpoint.strftime('%Y%m%d')}",
        )])
    buttons.append([InlineKeyboardButton(text="✍️ Boshqa sana kiritish", callback_data=f"fstart:custom:{object_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def fine_admin_kb(fine_id: int, workers: Optional[Dict[int, str]] = None) -> InlineKeyboardMarkup:
    """Jarima xabari ostidagi tugmalar. workers berilsa — ishchini tanlash tugmalari ham chiqadi."""
    buttons = []
    for uid, name in list((workers or {}).items())[:30]:
        buttons.append([InlineKeyboardButton(text=f"👤 {name}"[:60], callback_data=f"fine:assign:{fine_id}:{uid}")])
    buttons.append([InlineKeyboardButton(text="❌ Jarimani bekor qilish", callback_data=f"fine:cancel:{fine_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def fines_menu_kb() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="🗓 Obyektlar: sana va muddat (kun)", callback_data="fstart:list")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def period_days_kb(object_id: int, default_days: int) -> InlineKeyboardMarkup:
    """Obyekt uchun borilish muddatini (kun) tanlash"""
    row = [
        InlineKeyboardButton(text=f"{n} kun", callback_data=f"flimit:set:{object_id}:{n}")
        for n in (3, 5, 7, 10, 14)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[
        row,
        [InlineKeyboardButton(text="✍️ Boshqa son kiritish", callback_data=f"flimit:custom:{object_id}")],
        [InlineKeyboardButton(text=f"↩️ Standart ({default_days} kun)", callback_data=f"flimit:set:{object_id}:0")],
    ])


def object_fine_settings_kb(object_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗓 Boshlanish sanasini o'zgartirish", callback_data=f"fstart:dates:{object_id}")],
        [InlineKeyboardButton(text="⏱ Muddatni (kun) o'zgartirish", callback_data=f"flimit:ask:{object_id}")],
    ])


def start_dates_list_kb(
    objects: List[Dict[str, Any]], days_by_obj: Optional[Dict[int, int]] = None, default_days: int = 7
) -> InlineKeyboardMarkup:
    days_by_obj = days_by_obj or {}
    buttons = []
    for obj in objects:
        raw = obj.get("start_date")
        label = f"{raw[8:10]}.{raw[5:7]}.{raw[:4]}" if raw else "❓ kiritilmagan"
        buttons.append([InlineKeyboardButton(
            text=f"🏗 {obj.get('name', '?')[:30]} — {label} · {days_by_obj.get(obj.get('id')) or default_days} kun",
            callback_data=f"fstart:pick:{obj.get('id', 0)}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
