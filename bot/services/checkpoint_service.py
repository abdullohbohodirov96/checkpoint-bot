"""
Checkpoint tekshirish xizmati.
Haversine formulasi orqali masofa hisoblash va checkpoint saqlash.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.models.models import Checkpoint, Object
from bot.utils.haversine import haversine


class CheckpointService:
    """Checkpoint tekshirish va saqlash"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ──────────────────────────────────────────
    # TEKSHIRISH
    # ──────────────────────────────────────────

    def verify_location(
        self,
        user_lat: float,
        user_lon: float,
        obj: Object,
    ) -> Tuple[float, bool]:
        """
        Foydalanuvchi lokatsiyasini obyekt bilan solishtirish.
        Returns: (masofa_metrda, qabul_qilindimi)
        """
        distance = haversine(user_lat, user_lon, obj.latitude, obj.longitude)
        is_accepted = distance <= obj.radius
        return distance, is_accepted

    # ──────────────────────────────────────────
    # CHECKPOINT SAQLASH
    # ──────────────────────────────────────────

    async def save_checkpoint(
        self,
        user_id: int,
        object_id: int,
        user_latitude: float,
        user_longitude: float,
        distance_in_meters: float,
        status: str,
    ) -> Checkpoint:
        """Checkpoint qaydini saqlash"""
        checkpoint = Checkpoint(
            user_id=user_id,
            object_id=object_id,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            distance_in_meters=distance_in_meters,
            status=status,
        )
        self.session.add(checkpoint)
        await self.session.flush()
        return checkpoint

    # ──────────────────────────────────────────
    # FOYDALANUVCHI TARIXINI OLISH
    # ──────────────────────────────────────────

    async def get_user_history(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Checkpoint]:
        """Foydalanuvchi checkpoint tarixini olish"""
        stmt = (
            select(Checkpoint)
            .options(selectinload(Checkpoint.object))
            .where(Checkpoint.user_id == user_id)
            .order_by(Checkpoint.checked_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_checkpoint_count(self, user_id: int) -> int:
        stmt = select(func.count()).select_from(Checkpoint).where(Checkpoint.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    # ──────────────────────────────────────────
    # ADMIN — BARCHA TARIX
    # ──────────────────────────────────────────

    async def get_all_history(
        self,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Checkpoint]:
        """Barcha checkpoint tarixini olish (admin uchun)"""
        stmt = (
            select(Checkpoint)
            .options(
                selectinload(Checkpoint.object),
                selectinload(Checkpoint.user),
            )
            .order_by(Checkpoint.checked_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_checkpoint_count(self) -> int:
        stmt = select(func.count()).select_from(Checkpoint)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    # ──────────────────────────────────────────
    # OBYEKTLAR
    # ──────────────────────────────────────────

    async def get_all_objects(self) -> List[Object]:
        """Barcha obyektlarni olish"""
        stmt = select(Object).order_by(Object.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_object_by_id(self, object_id: int) -> Optional[Object]:
        stmt = select(Object).where(Object.id == object_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_object(
        self,
        name: str,
        latitude: float,
        longitude: float,
        radius: int = 500,
    ) -> Object:
        """Yangi obyekt qo'shish"""
        obj = Object(
            name=name,
            latitude=latitude,
            longitude=longitude,
            radius=radius,
        )
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def delete_object(self, object_id: int) -> bool:
        """Obyektni o'chirish"""
        obj = await self.get_object_by_id(object_id)
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True
