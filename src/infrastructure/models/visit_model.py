import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, DateTime, Text, Enum, ForeignKey, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship
from src.infrastructure.database import Base


class VisitStatus(str, enum.Enum):
    DRAFT = "DRAFT"    # rozpracovaný koncept – lze měnit
    CLOSED = "CLOSED"  # uzavřená návštěva – neměnná, podklad pro výkaz


class VisitModel(Base):
    """Záznam o uskutečněné návštěvě (1:1 k rezervaci)."""

    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), unique=True, nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    status = Column(Enum(VisitStatus), default=VisitStatus.DRAFT, nullable=False)
    clinical_note = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    appointment = relationship("AppointmentModel", back_populates="visit")
    doctor = relationship("DoctorModel")
    patient = relationship("PatientModel")
    closed_by = relationship("UserModel", foreign_keys=[closed_by_user_id])
    items = relationship(
        "VisitProcedureModel",
        back_populates="visit",
        cascade="all, delete-orphan",
        order_by="VisitProcedureModel.id",
    )

    @property
    def total_points(self) -> int:
        return sum(item.total_points for item in self.items)

    def __repr__(self) -> str:
        return f"<Visit id={self.id} appointment={self.appointment_id} {self.status}>"


class VisitProcedureModel(Base):
    """Asociační entita M:N Návštěva ↔ Výkon s počtem a bodovou hodnotou.

    `points_per_unit` je snapshot bodů v okamžiku zápisu – pozdější změna
    číselníku nezmění historii návštěv ani měsíční výkaz.
    """

    __tablename__ = "visit_procedures"
    __table_args__ = (
        UniqueConstraint("visit_id", "procedure_id", name="uq_visit_procedures_visit_procedure"),
        CheckConstraint("quantity >= 1", name="ck_visit_procedures_quantity"),
        CheckConstraint("points_per_unit >= 0", name="ck_visit_procedures_points"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    visit_id = Column(Integer, ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True)
    procedure_id = Column(Integer, ForeignKey("procedures.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    points_per_unit = Column(Integer, nullable=False)

    visit = relationship("VisitModel", back_populates="items")
    procedure = relationship("ProcedureModel")

    @property
    def total_points(self) -> int:
        return self.quantity * self.points_per_unit
