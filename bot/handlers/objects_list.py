"""
Obyektlar ro'yxatini ko'rish — bo'sh modul.
Admin uchun admin.py ichida qilingan.
Oddiy foydalanuvchi menyusida bu tugma yo'q.
"""

from aiogram import Router

router = Router(name="objects_list")

# Oddiy foydalanuvchida "Obyektlar ro'yxati" tugmasi yo'q.
# Admin uchun admin.py dagi list_objects handleri ishlaydi.
