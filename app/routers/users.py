"""Users router: profile management and lookup."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_manager_or_admin
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserResponse, UserUpdateRequest, UserWithCompanyResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserWithCompanyResponse,
    summary="Perfil completo do usuário logado",
)
async def get_my_profile(current_user: CurrentUser) -> User:
    """Retorna o perfil completo incluindo dados da empresa vinculada."""
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Atualizar perfil do usuário logado",
)
async def update_my_profile(
    body: UserUpdateRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Atualiza **full_name** e/ou **avatar_initials** do usuário autenticado.
    Campos não enviados permanecem inalterados.
    """
    if body.full_name is not None:
        current_user.full_name = body.full_name
        # Recalculate initials if not explicitly provided
        if body.avatar_initials is None:
            current_user.avatar_initials = current_user.computed_initials

    if body.avatar_initials is not None:
        current_user.avatar_initials = body.avatar_initials.upper()

    db.add(current_user)
    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.get(
    "/{user_id}",
    response_model=UserWithCompanyResponse,
    summary="Buscar usuário por ID (admin/manager)",
    dependencies=[require_manager_or_admin()],
)
async def get_user_by_id(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: CurrentUser,
) -> User:
    """
    Retorna dados completos de um usuário pelo UUID.
    Requer role **manager** ou **admin**.
    Managers só podem visualizar usuários da própria empresa.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    # Managers can only see users of their own company
    if (
        _current_user.role == UserRole.manager
        and user.company_id != _current_user.company_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para visualizar este usuário.",
        )

    return user
