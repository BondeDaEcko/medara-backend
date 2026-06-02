"""Company model — tenant entity that owns users."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class CompanyPlan(str, enum.Enum):
    essential = "essential"
    professional = "professional"
    gold = "gold"


class Company(Base, UUIDMixin):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    plan: Mapped[CompanyPlan] = mapped_column(
        Enum(CompanyPlan, name="company_plan"),
        default=CompanyPlan.essential,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Asaas billing
    asaas_customer_id:    Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    asaas_subscription_id: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    payment_status: Mapped[str] = mapped_column(String(20), default="trial", nullable=False)
    blocked_at:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_due_date: Mapped[Optional[date]]     = mapped_column(Date, nullable=True)

    # Relationships
    users: Mapped[List["User"]] = relationship(  # noqa: F821
        "User", back_populates="company", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Company id={self.id} name={self.name!r}>"
