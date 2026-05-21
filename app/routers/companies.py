"""Companies router: create, fetch, list members, invite."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_admin, require_manager_or_admin
from app.core.security import hash_password
from app.database import get_db
from app.models.company import Company
from app.models.user import User, UserRole
from app.schemas.company import CompanyCreate, CompanyInviteRequest, CompanyResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar empresa (admin)",
    dependencies=[require_admin()],
)
async def create_company(
    body: CompanyCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: CurrentUser,
) -> Company:
    """
    Cria uma nova empresa na plataforma.
    Requer role **admin**.
    """
    if body.domain:
        existing = await db.execute(
            select(Company).where(Company.domain == body.domain)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe uma empresa com este domínio.",
            )

    company = Company(name=body.name, domain=body.domain, plan=body.plan)
    db.add(company)
    await db.flush()
    await db.refresh(company)
    return company


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    summary="Dados da empresa",
)
async def get_company(
    company_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Company:
    """
    Retorna dados de uma empresa.
    Funcionários só podem ver a própria empresa; managers e admins podem ver qualquer uma.
    """
    company = await _fetch_company_or_404(company_id, db)

    if current_user.role == UserRole.employee and current_user.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para visualizar esta empresa.",
        )

    return company


@router.get(
    "/{company_id}/users",
    response_model=list[UserResponse],
    summary="Listar funcionários da empresa (manager/admin)",
    dependencies=[require_manager_or_admin()],
)
async def list_company_users(
    company_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[User]:
    """
    Lista todos os usuários de uma empresa.
    Requer role **manager** (apenas sua própria empresa) ou **admin** (qualquer empresa).
    """
    await _fetch_company_or_404(company_id, db)

    if current_user.role == UserRole.manager and current_user.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode listar funcionários da sua própria empresa.",
        )

    result = await db.execute(select(User).where(User.company_id == company_id))
    return list(result.scalars().all())


@router.post(
    "/{company_id}/invite",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Convidar funcionário por e-mail",
    dependencies=[require_manager_or_admin()],
)
async def invite_employee(
    company_id: uuid.UUID,
    body: CompanyInviteRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Cria um novo usuário **employee** vinculado à empresa e envia convite por e-mail.
    Nesta fase, o usuário é criado com senha temporária aleatória e `is_verified=False`.
    Requer role **manager** (apenas sua própria empresa) ou **admin**.

    - Em produção: integrar com serviço de e-mail para envio do link de ativação.
    """
    await _fetch_company_or_404(company_id, db)

    if current_user.role == UserRole.manager and current_user.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode convidar funcionários para a sua própria empresa.",
        )

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está cadastrado na plataforma.",
        )

    import secrets

    temp_password = secrets.token_urlsafe(16)
    user = User(
        email=body.email,
        hashed_password=hash_password(temp_password),
        full_name=body.full_name,
        role=UserRole.employee,
        company_id=company_id,
        is_verified=False,
    )
    user.avatar_initials = user.computed_initials
    db.add(user)
    await db.flush()
    await db.refresh(user)

    # TODO (Phase 2): trigger email invitation with activation link
    return user


async def _fetch_company_or_404(
    company_id: uuid.UUID, db: AsyncSession
) -> Company:
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada.",
        )
    return company
