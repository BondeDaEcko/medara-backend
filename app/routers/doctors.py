"""Doctors router: register profile, list, fetch, toggle availability."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, require_doctor
from app.database import get_db
from app.models.doctor import Doctor, DoctorSpecialty, Specialty
from app.models.user import User, UserRole
from app.schemas.doctor import (
    DoctorAvailabilityUpdate,
    DoctorListResponse,
    DoctorRegisterRequest,
    DoctorResponse,
)

router = APIRouter(prefix="/doctors", tags=["doctors"])


def _build_doctor_response(doctor: Doctor) -> DoctorResponse:
    """Map Doctor ORM instance to DoctorResponse, flattening user fields."""
    return DoctorResponse(
        id=doctor.id,
        user_id=doctor.user_id,
        crm=doctor.crm,
        crm_state=doctor.crm_state,
        bio=doctor.bio,
        is_available=doctor.is_available,
        rating_avg=doctor.rating_avg,
        rating_count=doctor.rating_count,
        created_at=doctor.created_at,
        specialties=doctor.specialties,
        full_name=doctor.user.full_name if doctor.user else None,
        email=doctor.user.email if doctor.user else None,
        avatar_initials=doctor.user.avatar_initials if doctor.user else None,
    )


def _build_doctor_list_response(doctor: Doctor) -> DoctorListResponse:
    return DoctorListResponse(
        id=doctor.id,
        user_id=doctor.user_id,
        crm=doctor.crm,
        crm_state=doctor.crm_state,
        bio=doctor.bio,
        is_available=doctor.is_available,
        rating_avg=doctor.rating_avg,
        rating_count=doctor.rating_count,
        specialties=doctor.specialties,
        full_name=doctor.user.full_name if doctor.user else None,
        avatar_initials=doctor.user.avatar_initials if doctor.user else None,
    )


@router.post(
    "/register",
    response_model=DoctorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Médico cria perfil profissional",
    dependencies=[require_doctor()],
)
async def register_doctor(
    body: DoctorRegisterRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DoctorResponse:
    """
    Registra o perfil profissional do médico (CRM, bio, especialidades).
    O usuário já deve existir com **role=doctor**.
    Cada usuário pode ter apenas um perfil de médico.
    """
    existing = await db.execute(
        select(Doctor).where(Doctor.user_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Perfil de médico já cadastrado para este usuário.",
        )

    doctor = Doctor(
        user_id=current_user.id,
        crm=body.crm,
        crm_state=body.crm_state.upper(),
        bio=body.bio,
    )
    db.add(doctor)
    await db.flush()

    # Associate specialties by ID
    all_specs: list[Specialty] = []
    if body.specialty_ids:
        spec_result = await db.execute(
            select(Specialty).where(Specialty.id.in_(body.specialty_ids))
        )
        found_specs = spec_result.scalars().all()
        found_ids = {s.id for s in found_specs}
        missing = set(body.specialty_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Especialidades não encontradas: {[str(i) for i in missing]}",
            )
        all_specs.extend(found_specs)

    # Associate specialties by name (create if not exists)
    for name in body.specialty_names:
        name = name.strip()
        if not name:
            continue
        res = await db.execute(select(Specialty).where(Specialty.name == name))
        spec = res.scalar_one_or_none()
        if not spec:
            spec = Specialty(name=name)
            db.add(spec)
            await db.flush()
        all_specs.append(spec)

    for spec in all_specs:
        db.add(DoctorSpecialty(doctor_id=doctor.id, specialty_id=spec.id))

    await db.flush()
    await db.refresh(doctor)

    # Eager load relationships for response
    result = await db.execute(
        select(Doctor)
        .options(selectinload(Doctor.user), selectinload(Doctor.specialties))
        .where(Doctor.id == doctor.id)
    )
    doctor = result.scalar_one()
    return _build_doctor_response(doctor)


@router.get(
    "",
    response_model=list[DoctorListResponse],
    summary="Listar médicos com filtros opcionais",
)
async def list_doctors(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: CurrentUser,
    specialty_id: uuid.UUID | None = Query(default=None, description="Filtrar por especialidade"),
    available_only: bool = Query(default=False, description="Apenas médicos disponíveis agora"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[DoctorListResponse]:
    """
    Lista médicos cadastrados na plataforma.
    Suporta filtro por especialidade e disponibilidade imediata.
    """
    stmt = (
        select(Doctor)
        .options(selectinload(Doctor.user), selectinload(Doctor.specialties))
        .join(User, Doctor.user_id == User.id)
        .where(User.is_active.is_(True))
    )

    if available_only:
        stmt = stmt.where(Doctor.is_available.is_(True))

    if specialty_id:
        stmt = stmt.join(
            DoctorSpecialty, DoctorSpecialty.doctor_id == Doctor.id
        ).where(DoctorSpecialty.specialty_id == specialty_id)

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    doctors = result.scalars().unique().all()
    return [_build_doctor_list_response(d) for d in doctors]


@router.get(
    "/{doctor_id}",
    response_model=DoctorResponse,
    summary="Perfil completo do médico",
)
async def get_doctor(
    doctor_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: CurrentUser,
) -> DoctorResponse:
    """Retorna o perfil completo de um médico pelo UUID do Doctor."""
    result = await db.execute(
        select(Doctor)
        .options(selectinload(Doctor.user), selectinload(Doctor.specialties))
        .where(Doctor.id == doctor_id)
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Médico não encontrado.",
        )
    return _build_doctor_response(doctor)


@router.patch(
    "/me/availability",
    response_model=DoctorResponse,
    summary="Médico ativa/desativa disponibilidade imediata",
    dependencies=[require_doctor()],
)
async def update_availability(
    body: DoctorAvailabilityUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DoctorResponse:
    """
    Alterna a flag **is_available** do médico autenticado.
    Quando `true`, o médico aparece disponível para consultas imediatas.
    """
    result = await db.execute(
        select(Doctor)
        .options(selectinload(Doctor.user), selectinload(Doctor.specialties))
        .where(Doctor.user_id == current_user.id)
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de médico não encontrado. Registre-se em POST /doctors/register.",
        )

    doctor.is_available = body.is_available
    db.add(doctor)
    await db.flush()
    await db.refresh(doctor)

    # Reload with relationships
    result = await db.execute(
        select(Doctor)
        .options(selectinload(Doctor.user), selectinload(Doctor.specialties))
        .where(Doctor.id == doctor.id)
    )
    doctor = result.scalar_one()
    return _build_doctor_response(doctor)
