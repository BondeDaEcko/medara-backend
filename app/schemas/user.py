"""Pydantic schemas for User endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole
from app.schemas.company import CompanyResponse


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    company_id: uuid.UUID | None
    is_active: bool
    is_verified: bool
    avatar_initials: str | None
    created_at: datetime
    updated_at: datetime


class UserWithCompanyResponse(UserResponse):
    company: CompanyResponse | None = None


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    avatar_initials: str | None = Field(default=None, min_length=1, max_length=4)
