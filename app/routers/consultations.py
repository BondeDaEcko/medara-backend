"""
MEDARA — Router de Consultas / Videochamadas.

Gera o token Agora e o nome do canal para cada sessão de videochamada.
O funcionário e o médico entram no mesmo canal usando este token.
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import settings
from app.core.deps import CurrentUser

router = APIRouter(prefix="/consultations", tags=["consultations"])


# ── Schemas ────────────────────────────────────────────────────────────────

class CallTokenRequest(BaseModel):
    doctor_id: uuid.UUID | None = None   # ID do médico (opcional por enquanto)
    specialty: str = "Consulta Geral"


class CallTokenResponse(BaseModel):
    channel: str      # nome único do canal Agora para esta consulta
    token: str | None # token Agora (None em modo de teste)
    app_id: str       # App ID do Agora (vai para o frontend)
    uid: int          # UID único do participante neste canal
    expires_in: int   # segundos até o token expirar


# ── Gerador de token Agora ──────────────────────────────────────────────────

def _build_agora_token(channel: str, uid: int, expire_seconds: int = 3600) -> str | None:
    """
    Gera token RTC do Agora usando App ID + App Certificate.
    Retorna None se as credenciais não estiverem configuradas (modo dev).
    """
    if not settings.agora_app_id or not settings.agora_app_certificate:
        return None

    try:
        from agora_token_builder import RtcTokenBuilder, Role_Publisher  # type: ignore
        expire_ts = int(time.time()) + expire_seconds
        token = RtcTokenBuilder.buildTokenWithUid(
            settings.agora_app_id,
            settings.agora_app_certificate,
            channel,
            uid,
            Role_Publisher,
            expire_ts,
        )
        return token
    except Exception:
        return None


# ── Endpoint ────────────────────────────────────────────────────────────────

@router.post(
    "/token",
    response_model=CallTokenResponse,
    summary="Obter token para entrar em videochamada",
)
async def get_call_token(
    body: CallTokenRequest,
    current_user: CurrentUser,
) -> CallTokenResponse:
    """
    Cria uma sessão de videochamada e retorna:
    - **channel**: nome único do canal (compartilhado entre médico e paciente)
    - **token**: token de autenticação Agora (null em modo de teste)
    - **app_id**: ID do aplicativo Agora para o SDK do frontend
    - **uid**: identificador único do participante no canal

    O médico e o funcionário devem usar o mesmo **channel** para se encontrar.
    """
    if not settings.agora_app_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Videochamada não configurada. "
                "Configure AGORA_APP_ID no servidor. "
                "Crie sua conta em: https://console.agora.io"
            ),
        )

    # Canal único por consulta — baseado em UUIDs dos participantes + timestamp
    channel = f"medara-{uuid.uuid4().hex[:12]}"
    uid     = abs(hash(str(current_user.id))) % 100_000
    token   = _build_agora_token(channel, uid)

    return CallTokenResponse(
        channel=channel,
        token=token,
        app_id=settings.agora_app_id,
        uid=uid,
        expires_in=3600,
    )
