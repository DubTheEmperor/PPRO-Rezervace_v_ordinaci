from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from src.infrastructure.database import Base


class DoctorSickDayModel(Base):
    """Den, kdy je lékař nemocný (mimořádná nedostupnost, otevřený bod 5).

    Jeden záznam = jeden celý den. UNIQUE(doctor_id, day) brání duplicitám;
    souvislá období se skládají až v byznys vrstvě.
    """

    __tablename__ = "doctor_sick_days"
    __table_args__ = (
        UniqueConstraint("doctor_id", "day", name="uq_doctor_sick_days_doctor_day"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    day = Column(Date, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    doctor = relationship("DoctorModel")

    def __repr__(self) -> str:
        return f"<DoctorSickDay doctor={self.doctor_id} day={self.day}>"
