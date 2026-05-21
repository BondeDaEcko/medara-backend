"""Authentication router: register, login, refresh, logout, me."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

_limiter = Limiter(key_func=get_remote_address)
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_expiry_datetime,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.user import RefreshToken, User, UserRole
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar novo funcionário",
)
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Registra um novo usuário com role **employee**.

    - **email**: deve ser único na plataforma
    - **company_id**: UUID da empresa (opcional — pode ser associado depois)
    """
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está cadastrado.",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=UserRole.employee,
        company_id=body.company_id,
    )
    user.avatar_initials = user.computed_initials
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login e obtenção de tokens",
)
@_limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Autentica o usuário e retorna **access_token** (30 min) + **refresh_token** (7 dias).
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada. Entre em contato com o suporte.",
        )

    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token_str = create_refresh_token(str(user.id))

    stored_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=get_token_expiry_datetime(days=7),
    )
    db.add(stored_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
    )


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Renovar access token via refresh token",
)
async def refresh_token(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccessTokenResponse:
    """
    Troca um **refresh_token** válido por um novo **access_token**.
    O refresh_token não é rotacionado — permanece válido até expirar.
    """
    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido ou expirado.",
    )

    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise invalid_exc
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise invalid_exc

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == body.refresh_token,
            RefreshToken.revoked.is_(False),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    stored = result.scalar_one_or_none()
    if not stored:
        raise invalid_exc

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise invalid_exc

    new_access = create_access_token(str(user.id), user.role.value)
    return AccessTokenResponse(access_token=new_access)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Invalidar refresh token (logout)",
)
async def logout(
    body: LogoutRequest,
    _current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Revoga o **refresh_token** fornecido.
    O access_token expirará naturalmente em até 30 minutos.
    """
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == body.refresh_token,
            RefreshToken.user_id == _current_user.id,
        )
    )
    stored = result.scalar_one_or_none()
    if stored:
        stored.revoked = True
    return {"detail": "Logout realizado com sucesso."}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Dados do usuário autenticado",
)
async def me(current_user: CurrentUser) -> User:
    """Retorna os dados do usuário atualmente autenticado via Bearer token."""
    return current_user
