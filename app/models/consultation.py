"""Consultation model — connects employee with doctor."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class ConsultationStatus(str, enum.Enum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class Consultation(Base, UUIDMixin):
    __tablename__ = "consultations"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    specialty_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("specialties.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[ConsultationStatus] = mapped_column(
        Enum(ConsultationStatus, name="consultation_status"),
        default=ConsultationStatus.scheduled,
        nullable=False,
    )
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    employee: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[employee_id],
        back_populates="consultations_as_employee",
    )
    doctor: Mapped["Doctor"] = relationship(  # noqa: F821
        "Doctor", back_populates="consultations"
    )
    specialty: Mapped["Specialty"] = relationship(  # noqa: F821
        "Specialty", back_populates="consultations"
    )

    def __repr__(self) -> str:
        return (
            f"<Consultation id={self.id} status={self.status} "
            f"employee={self.employee_id} doctor={self.doctor_id}>"
        )
