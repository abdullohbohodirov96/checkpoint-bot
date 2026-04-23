"""
Foydalanuvchi uchun Telegram klaviaturalari.
Oddiy, doimiy reply keyboard tugmalar.
"""

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from typing import List, Dict, Any


# ──────────────────────────────────────────────────
# ODDIY FOYDALANUVCHI MENYUSI
# ──────────────────────────────────────────────────

def main_menu_kb() -> ReplyKeyboardMarkup:
    """
    Oddiy foydalanuvchi uchun doimiy menyu.
    4 ta tugma.
    """
    keyboard = [
        [KeyboardButton(text="📍 Checkpoint qilish")],
        [
            KeyboardButton(text="📋 Mening tarixim"),
            KeyboardButton(text="❓ Yordam"),
        ],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Tugmani tanlang...",
    )


# ──────────────────────────────────────────────────
# CHECKPOINT — OBYEKT TANLASH
# ──────────────────────────────────────────────────

def objects_inline_kb(objects: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Obyektlar ro'yxati — inline tugmalar"""
    buttons = []
    for obj in objects:
        buttons.append([
            InlineKeyboardButton(
                text=f"🏗 {obj['name']}",
                callback_data=f"select_object:{obj['id']}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="❌ Bekor qilish",
            callback_data="cancel_checkpoint",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ──────────────────────────────────────────────────
# MAQSAD (PURPOSE) TANLASH
# ──────────────────────────────────────────────────

def purpose_inline_kb() -> InlineKeyboardMarkup:
    """Nima qilishga kelganligini tanlash"""
    buttons = [
        [InlineKeyboardButton(text="🧹 Pelesos qilishga", callback_data="purpose:pelesos")],
        [InlineKeyboardButton(text="💧 Promifka qilishga", callback_data="purpose:promifka")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_checkpoint")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ──────────────────────────────────────────────────
# LOKATSIYA SO'RASH
# ──────────────────────────────────────────────────

def location_request_kb() -> ReplyKeyboardMarkup:
    """Lokatsiya yuborish tugmasi"""
    keyboard = [
        [
            KeyboardButton(
                text="📍 Joylashuvni yuborish",
                request_location=True,
            )
        ],
        [KeyboardButton(text="❌ Bekor qilish")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Joylashuvingizni yuboring...",
    )


# ──────────────────────────────────────────────────
# QAYTA URINISH
# ──────────────────────────────────────────────────

def retry_kb() -> InlineKeyboardMarkup:
    """Checkpoint rad etilganda qayta urinish"""
    buttons = [
        [InlineKeyboardButton(text="🔄 Qayta urinish", callback_data="retry_checkpoint")],
        [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="go_main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ──────────────────────────────────────────────────
# TARIX — SAHIFALASH
# ──────────────────────────────────────────────────

def history_pagination_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Tarix uchun sahifalash tugmalari"""
    buttons = []
    nav = []

    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"history_page:{page - 1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"history_page:{page + 1}"))

    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)
