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
from typing import List, Dict, Any


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
