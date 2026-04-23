"""
Supabase ulanishi.
"""

from supabase import Client, create_client
from bot.config import get_settings
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

# Supabase Client Singleton
_supabase: Client = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            logger.error("❌ SUPABASE_URL yoki SUPABASE_KEY topilmadi!")
            raise ValueError("Missing Supabase credentials")
        _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase

async def init_db():
    """
    Ma'lumotlar bazasi tayyorligini tekshirish.
    Supabase'da table'lar bor-yo'qligini, yoki default object qo'shishni tekshiramiz.
    """
    try:
        sb = get_supabase()
        
        # Default obyektni tekshirish
        res = sb.table("objects").select("*").eq("name", "Nurziyo 32").execute()
        
        if not res.data:
            sb.table("objects").insert({
                "name": "Nurziyo 32",
                "latitude": 41.390166,
                "longitude": 69.271265,
                "radius": 500
            }).execute()
            logger.info("✅ Default obyekt qo'shildi: Nurziyo 32")
        else:
            logger.info("ℹ️ Default obyekt mavjud: Nurziyo 32")
            
        logger.info("✅ Supabase ulanishi muvaffaqiyatli o'rnatildi")
    except Exception as e:
        logger.error(f"❌ Supabase ulanishida xatolik: {e}")
