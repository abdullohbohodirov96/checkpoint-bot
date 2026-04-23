"""
Database ulanish, session boshqaruvi va default ma'lumotlar.
SQLite va PostgreSQL ni qo'llab-quvvatlaydi.
"""

from sqlalchemy import select, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from bot.config import get_settings
from bot.models.models import Base, Object

settings = get_settings()

# Engine parametrlari
engine_kwargs = {
    "echo": False,
}

# SQLite uchun maxsus sozlamalar
if settings.is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 5

# Async engine
engine = create_async_engine(
    settings.async_database_url,
    **engine_kwargs,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """
    Jadvallarni yaratish va default obyektni qo'shish.
    """
    # 1. Jadvallar yaratish
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database jadvallar tayyor")

    # 2. Default obyektni qo'shish (agar mavjud bo'lmasa)
    async with async_session() as session:
        stmt = select(Object).where(Object.name == "Nurziyo 32")
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            default_obj = Object(
                name="Nurziyo 32",
                latitude=41.390166,
                longitude=69.271265,
                radius=500,
            )
            session.add(default_obj)
            await session.commit()
            print("✅ Default obyekt qo'shildi: Nurziyo 32")
        else:
            print("ℹ️ Default obyekt mavjud: Nurziyo 32")


async def get_session() -> AsyncSession:
    """Yangi DB session qaytaradi"""
    async with async_session() as session:
        return session
