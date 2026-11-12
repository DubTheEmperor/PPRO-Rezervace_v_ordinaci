import enum
from sqlalchemy import Column, Integer, String, Time, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from src.infrastructure.database import Base


class OfficeHoursKind(str, enum.Enum):
    OFFICE = "OFFICE"        # lékař ordinuje v ordinaci – na blok lze rezervovat
    ELSEWHERE = "ELSEWHERE"  # lékař ordinuje na jiném pracovišti – rezervovat nelze


class OfficeHoursModel(Base):
    """Pravidelný týdenní blok ordinačních hodin lékaře (0 = pondělí … 6 = neděle).

    Blok typu ELSEWHERE označuje pravidelný čas, kdy lékař ordinuje jinde
    (`location` = kde); v kalendáři se zobrazí, ale nedá se na něj objednat.
    """

    __tablename__ = "office_hours"
    __table_args__ = (
        CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_office_hours_weekday"),
        CheckConstraint("start_time < end_time", name="ck_office_hours_range"),
        CheckConstraint("kind IN ('OFFICE', 'ELSEWHERE')", name="ck_office_hours_kind"),
        CheckConstraint("kind = 'OFFICE' OR location IS NOT NULL", name="ck_office_hours_location"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    weekday = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    kind = Column(String(16), nullable=False, default=OfficeHoursKind.OFFICE.value, server_default="OFFICE")
    location = Column(String(100), nullable=True)

    doctor = relationship("DoctorModel", back_populates="office_hours")

    @property
    def is_bookable(self) -> bool:
        return self.kind == OfficeHoursKind.OFFICE.value

    def __repr__(self) -> str:
        return f"<OfficeHours doctor={self.doctor_id} day={self.weekday} {self.start_time}-{self.end_time} {self.kind}>"
