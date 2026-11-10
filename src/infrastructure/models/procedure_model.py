from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, CheckConstraint
from src.infrastructure.database import Base


class ProcedureModel(Base):
    """Položka centrálního číselníku zdravotních výkonů (kód, název, bodové ohodnocení)."""

    __tablename__ = "procedures"
    __table_args__ = (
        CheckConstraint("points >= 0", name="ck_procedures_points"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    points = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<Procedure {self.code} '{self.name}' {self.points} b>"
