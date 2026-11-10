from sqlalchemy import Column, Integer, Time, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from src.infrastructure.database import Base


class OfficeHoursModel(Base):
    """Pravidelný týdenní blok ordinačních hodin lékaře (0 = pondělí … 6 = neděle)."""

    __tablename__ = "office_hours"
    __table_args__ = (
        CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_office_hours_weekday"),
        CheckConstraint("start_time < end_time", name="ck_office_hours_range"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    weekday = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    doctor = relationship("DoctorModel", back_populates="office_hours")

    def __repr__(self) -> str:
        return f"<OfficeHours doctor={self.doctor_id} day={self.weekday} {self.start_time}-{self.end_time}>"
