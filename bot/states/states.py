"""
FSM (Finite State Machine) holatlari.
"""

from aiogram.fsm.state import State, StatesGroup


class CheckpointStates(StatesGroup):
    """Checkpoint qilish jarayoni"""
    selecting_object = State()    # Obyektni tanlash
    waiting_location = State()    # Lokatsiya kutish


class AdminAddObjectStates(StatesGroup):
    """Admin: yangi obyekt qo'shish"""
    entering_name = State()
    entering_latitude = State()
    entering_longitude = State()
    entering_radius = State()
