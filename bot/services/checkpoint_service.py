"""
Checkpoint tekshirish xizmati.
Haversine formulasi orqali masofa hisoblash va supabase orqali saqlash.
"""

from typing import Optional, List, Tuple, Dict, Any
from bot.utils.haversine import haversine
from bot.database.db import get_supabase


class CheckpointService:
    """Checkpoint tekshirish va saqlash"""

    def __init__(self):
        self.sb = get_supabase()

    # ──────────────────────────────────────────
    # TEKSHIRISH
    # ──────────────────────────────────────────

    def verify_location(
        self,
        user_lat: float,
        user_lon: float,
        obj: Dict[str, Any],
    ) -> Tuple[float, bool]:
        """
        Foydalanuvchi lokatsiyasini obyekt bilan solishtirish.
        Returns: (masofa_metrda, qabul_qilindimi)
        """
        distance = haversine(user_lat, user_lon, obj["latitude"], obj["longitude"])
        is_accepted = distance <= obj.get("radius", 500)
        return distance, is_accepted

    # ──────────────────────────────────────────
    # CHECKPOINT SAQLASH
    # ──────────────────────────────────────────

    def save_checkpoint(
        self,
        user_id: int,
        username: str,
        object_name: str,
        user_latitude: float,
        user_longitude: float,
        status: str,
        purpose: str,
    ) -> Dict[str, Any]:
        """Checkpoint qaydini saqlash"""
        data = {
            "user_id": user_id,
            "username": username,
            "object_name": object_name,
            "latitude": user_latitude,
            "longitude": user_longitude,
            "status": status,
            "purpose": purpose,
        }
        res = self.sb.table("checkpoints").insert(data).execute()
        return res.data[0] if res.data else data

    # ──────────────────────────────────────────
    # FOYDALANUVCHI TARIXINI OLISH
    # ──────────────────────────────────────────

    def get_user_history(
        self,
        user_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Foydalanuvchi checkpoint tarixini olish"""
        res = self.sb.table("checkpoints")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return res.data

    # ──────────────────────────────────────────
    # ADMIN — BARCHA TARIX
    # ──────────────────────────────────────────

    def get_all_history(
        self,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Barcha checkpoint tarixini olish (admin uchun)"""
        res = self.sb.table("checkpoints")\
            .select("*")\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return res.data

    # ──────────────────────────────────────────
    # OBYEKTLAR
    # ──────────────────────────────────────────

    def get_all_objects(self) -> List[Dict[str, Any]]:
        """Barcha obyektlarni olish"""
        res = self.sb.table("objects").select("*").order("name").execute()
        return res.data

    def get_object_by_id(self, object_id: int) -> Optional[Dict[str, Any]]:
        res = self.sb.table("objects").select("*").eq("id", object_id).execute()
        return res.data[0] if res.data else None

    def add_object(
        self,
        name: str,
        latitude: float,
        longitude: float,
        radius: int = 500,
    ) -> Dict[str, Any]:
        """Yangi obyekt qo'shish"""
        data = {
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius,
        }
        res = self.sb.table("objects").insert(data).execute()
        return res.data[0] if res.data else data

    def delete_object(self, object_id: int) -> bool:
        """Obyektni o'chirish"""
        res = self.sb.table("objects").delete().eq("id", object_id).execute()
        return len(res.data) > 0
