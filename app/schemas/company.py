"""Pydantic schemas for Company endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.company import CompanyPlan


class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    domain: str | None = Field(default=None, max_length=255)
    plan: CompanyPlan = CompanyPlan.essential


class CompanyResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    domain: str | None
    plan: CompanyPlan
    is_active: bool
    created_at: datetime


class CompanyInviteRequest(BaseModel):
    email: str = Field(max_length=320)
    full_name: str = Field(min_length=2, max_length=255)
