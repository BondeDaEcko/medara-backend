"""Pydantic schemas for Doctor endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SpecialtyResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str


class DoctorRegisterRequest(BaseModel):
    crm: str = Field(min_length=4, max_length=20)
    crm_state: str = Field(min_length=2, max_length=2)
    bio: str | None = Field(default=None, max_length=2000)
    specialty_ids: list[uuid.UUID] = Field(default_factory=list)
    specialty_names: list[str] = Field(default_factory=list, description="Cria especialidades pelo nome se não existirem")


class DoctorAvailabilityUpdate(BaseModel):
    is_available: bool


class DoctorResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    crm: str
    crm_state: str
    bio: str | None
    is_available: bool
    rating_avg: float
    rating_count: int
    created_at: datetime
    specialties: list[SpecialtyResponse] = []

    # Flattened user fields for convenience
    full_name: str | None = None
    email: str | None = None
    avatar_initials: str | None = None


class DoctorListResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    crm: str
    crm_state: str
    bio: str | None
    is_available: bool
    rating_avg: float
    rating_count: int
    specialties: list[SpecialtyResponse] = []
    full_name: str | None = None
    avatar_initials: str | None = None
