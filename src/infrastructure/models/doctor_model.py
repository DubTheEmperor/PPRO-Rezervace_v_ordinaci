from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.database import Base


class DoctorModel(Base):
    """Doménová entita lékaře ordinace (oddělená od přihlašovacího účtu)."""

    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # Volitelná vazba 1:1 na uživatelský účet – přes ni lékař spravuje vlastní ordinační hodiny
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    full_name = Column(String(100), nullable=False)
    specialization = Column(String(100), nullable=True)
    color = Column(String(7), nullable=False, default="#0284c7")
    # Identifikátory pro vykazování pojišťovnám (FP7) – IČP pracoviště a kód odbornosti
    icp = Column(String(8), nullable=True)
    specialty_code = Column(String(3), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    office_hours = relationship(
        "OfficeHoursModel",
        back_populates="doctor",
        cascade="all, delete-orphan",
        order_by="(OfficeHoursModel.weekday, OfficeHoursModel.start_time)",
    )

    def __repr__(self) -> str:
        return f"<Doctor id={self.id} name='{self.full_name}'>"
