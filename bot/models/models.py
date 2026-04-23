"""
Database modellari (ORM).

Jadvallar:
- User: Bot foydalanuvchilari (ishchilar va admin)
- Object: Ish joylari / obyektlar
- Checkpoint: Kelish qaydlari
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Float,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Bazaviy model"""
    pass


class User(Base):
    """
    Bot foydalanuvchilari jadvali.
    role: 'admin' yoki 'worker'
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    role = Column(String(20), default="worker", index=True)  # worker / admin
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    checkpoints = relationship("Checkpoint", back_populates="user", lazy="selectin")

    @property
    def display_name(self) -> str:
        """Ko'rsatiladigan ism"""
        if self.username:
            return f"@{self.username}"
        return self.full_name or "Noma'lum"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def __repr__(self):
        return f"<User(id={self.id}, tg_id={self.telegram_id}, role={self.role})>"


class Object(Base):
    """
    Ish joylari / obyektlar jadvali.
    Admin tomonidan qo'shiladi.
    """
    __tablename__ = "objects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius = Column(Integer, default=500)  # metrda
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    checkpoints = relationship("Checkpoint", back_populates="object", lazy="selectin")

    def __repr__(self):
        return f"<Object(id={self.id}, name={self.name})>"


class Checkpoint(Base):
    """
    Kelish qaydlari jadvali.
    """
    __tablename__ = "checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=False, index=True)
    user_latitude = Column(Float, nullable=False)
    user_longitude = Column(Float, nullable=False)
    distance_in_meters = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, index=True)  # accepted / rejected
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="checkpoints", lazy="selectin")
    object = relationship("Object", back_populates="checkpoints", lazy="selectin")

    # Indekslar
    __table_args__ = (
        Index("idx_cp_user_date", "user_id", "checked_at"),
    )

    def __repr__(self):
        return f"<Checkpoint(id={self.id}, status={self.status}, dist={self.distance_in_meters}m)>"
