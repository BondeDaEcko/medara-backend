"""Doctor, Specialty, and DoctorSpecialty models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class Specialty(Base, UUIDMixin):
    __tablename__ = "specialties"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    # Relationships
    doctor_specialties: Mapped[List["DoctorSpecialty"]] = relationship(
        "DoctorSpecialty", back_populates="specialty"
    )
    consultations: Mapped[List["Consultation"]] = relationship(  # noqa: F821
        "Consultation", back_populates="specialty"
    )

    def __repr__(self) -> str:
        return f"<Specialty id={self.id} name={self.name!r}>"


class DoctorSpecialty(Base):
    """Junction table: Doctor <-> Specialty (many-to-many)."""

    __tablename__ = "doctor_specialties"

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"),
        primary_key=True,
    )
    specialty_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("specialties.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Relationships
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="doctor_specialties")
    specialty: Mapped["Specialty"] = relationship(
        "Specialty", back_populates="doctor_specialties"
    )


class Doctor(Base, UUIDMixin):
    __tablename__ = "doctors"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    crm: Mapped[str] = mapped_column(String(20), nullable=False)
    crm_state: Mapped[str] = mapped_column(String(2), nullable=False)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rating_avg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="doctor_profile"
    )
    doctor_specialties: Mapped[List["DoctorSpecialty"]] = relationship(
        "DoctorSpecialty", back_populates="doctor", cascade="all, delete-orphan"
    )
    specialties: Mapped[List["Specialty"]] = relationship(
        "Specialty",
        secondary="doctor_specialties",
        viewonly=True,
        lazy="selectin",
    )
    consultations: Mapped[List["Consultation"]] = relationship(  # noqa: F821
        "Consultation", back_populates="doctor"
    )

    def __repr__(self) -> str:
        return f"<Doctor id={self.id} crm={self.crm}/{self.crm_state}>"
