import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, DateTime, Text, Enum, ForeignKey, UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.orm import relationship
from src.infrastructure.database import Base


class AppointmentStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    COMPLETED = "COMPLETED"
    CANCELLED_BY_PATIENT = "CANCELLED_BY_PATIENT"
    CANCELLED_BY_OFFICE = "CANCELLED_BY_OFFICE"
    NO_SHOW = "NO_SHOW"


class AppointmentModel(Base):
    """Rezervace termínu pacienta u lékaře.

    Časy `start_at` / `end_at` jsou naivní lokální čas ordinace (Europe/Prague).
    """

    __tablename__ = "appointments"
    __table_args__ = (
        Index("ix_appointments_doctor_start", "doctor_id", "start_at"),
        CheckConstraint("start_at < end_at", name="ck_appointments_range"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    start_at = Column(DateTime(timezone=False), nullable=False)
    end_at = Column(DateTime(timezone=False), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.PLANNED, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    doctor = relationship("DoctorModel")
    patient = relationship("PatientModel")
    created_by = relationship("UserModel")
    slots = relationship(
        "AppointmentSlotModel",
        back_populates="appointment",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Appointment id={self.id} doctor={self.doctor_id} {self.start_at}-{self.end_at} {self.status}>"


class AppointmentSlotModel(Base):
    """Obsazený 15minutový slot lékaře.

    UNIQUE(doctor_id, slot_start) je databázová pojistka proti překryvu rezervací –
    dva aktivní termíny nemohou obsadit tentýž slot téhož lékaře ani při souběhu.
    Při zrušení rezervace se sloty smažou (slot se uvolní), rezervace zůstává v historii.
    """

    __tablename__ = "appointment_slots"
    __table_args__ = (
        UniqueConstraint("doctor_id", "slot_start", name="uq_appointment_slots_doctor_slot"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    appointment_id = Column(
        Integer, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    slot_start = Column(DateTime(timezone=False), nullable=False)

    appointment = relationship("AppointmentModel", back_populates="slots")
