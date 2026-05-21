"""Pydantic schemas package."""

from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.company import CompanyCreate, CompanyInviteRequest, CompanyResponse
from app.schemas.doctor import (
    DoctorAvailabilityUpdate,
    DoctorListResponse,
    DoctorRegisterRequest,
    DoctorResponse,
    SpecialtyResponse,
)
from app.schemas.user import UserResponse, UserUpdateRequest, UserWithCompanyResponse

__all__ = [
    "AccessTokenResponse",
    "CompanyCreate",
    "CompanyInviteRequest",
    "CompanyResponse",
    "DoctorAvailabilityUpdate",
    "DoctorListResponse",
    "DoctorRegisterRequest",
    "DoctorResponse",
    "LoginRequest",
    "LogoutRequest",
    "RefreshRequest",
    "RegisterRequest",
    "SpecialtyResponse",
    "TokenResponse",
    "UserResponse",
    "UserUpdateRequest",
    "UserWithCompanyResponse",
]
