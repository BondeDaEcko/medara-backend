"""Billing router — Asaas integration for subscriptions and webhooks."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import asaas
from app.core.deps import CurrentUser, require_manager_or_admin
from app.database import get_db
from app.models.company import Company
from app.models.user import UserRole
from app.schemas.billing import (
    BillingStatusResponse,
    CreateCustomerRequest,
    PLAN_DESCRIPTIONS,
    PLAN_PRICES,
    SubscribeRequest,
)

logger = logging.getLogger("medara.billing")

router = APIRouter(prefix="/billing", tags=["billing"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_company_or_404(db: AsyncSession, company_id: str) -> Company:
    result = await db.execute(
        select(Company).where(Company.id == uuid.UUID(company_id))
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    return company


# ── Endpoints autenticados ────────────────────────────────────────────────────

@router.post(
    "/customer",
    summary="Cadastra empresa no Asaas",
    dependencies=[require_manager_or_admin()],
)
async def create_customer(
    payload: CreateCustomerRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Cria o customer no Asaas para uma empresa. Chamado uma vez no onboarding."""
    company = await _get_company_or_404(db, payload.company_id)

    if company.asaas_customer_id:
        return {"customer_id": company.asaas_customer_id, "already_exists": True}

    try:
        result = await asaas.create_customer(
            name=company.name,
            email=current_user.email,
            cpf_cnpj=payload.cpf_cnpj,
            phone=payload.phone,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao criar cliente no Asaas: {exc.response.text}",
        )

    company.asaas_customer_id = result["id"]
    await db.commit()
    logger.info("Asaas customer criado: %s → %s", company.name, result["id"])
    return {"customer_id": result["id"], "already_exists": False}


@router.post(
    "/subscribe",
    summary="Cria assinatura mensal no Asaas",
    dependencies=[require_manager_or_admin()],
)
async def subscribe(
    payload: SubscribeRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Cria uma assinatura recorrente mensal para a empresa."""
    company = await _get_company_or_404(db, payload.company_id)

    if not company.asaas_customer_id:
        raise HTTPException(
            status_code=400,
            detail="Empresa sem customer Asaas. Chame POST /billing/customer primeiro.",
        )
    if company.asaas_subscription_id:
        return {"subscription_id": company.asaas_subscription_id, "already_exists": True}

    value = PLAN_PRICES[payload.plan]
    description = PLAN_DESCRIPTIONS[payload.plan]

    try:
        result = await asaas.create_subscription(
            customer_id=company.asaas_customer_id,
            value=value,
            next_due_date=payload.next_due_date.isoformat(),
            description=description,
            billing_type=payload.billing_type,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao criar assinatura no Asaas: {exc.response.text}",
        )

    company.asaas_subscription_id = result["id"]
    company.payment_status = "active"
    company.next_due_date  = payload.next_due_date
    await db.commit()
    logger.info("Assinatura criada: %s → %s (R$ %.2f/mês)", company.name, result["id"], value)
    return {"subscription_id": result["id"], "value": value, "next_due_date": payload.next_due_date}


@router.get(
    "/status/{company_id}",
    response_model=BillingStatusResponse,
    summary="Status de pagamento de uma empresa",
    dependencies=[require_manager_or_admin()],
)
async def billing_status(company_id: str, db: DbSession) -> BillingStatusResponse:
    company = await _get_company_or_404(db, company_id)
    return BillingStatusResponse(
        company_id=str(company.id),
        payment_status=company.payment_status,
        is_active=company.is_active,
        asaas_customer_id=company.asaas_customer_id,
        asaas_subscription_id=company.asaas_subscription_id,
        next_due_date=company.next_due_date,
        blocked_at=company.blocked_at.isoformat() if company.blocked_at else None,
    )


@router.delete(
    "/cancel/{company_id}",
    summary="Cancela assinatura",
    dependencies=[require_manager_or_admin()],
)
async def cancel(company_id: str, db: DbSession) -> dict:
    company = await _get_company_or_404(db, company_id)
    if not company.asaas_subscription_id:
        raise HTTPException(status_code=400, detail="Empresa sem assinatura ativa.")
    try:
        await asaas.cancel_subscription(company.asaas_subscription_id)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Erro Asaas: {exc.response.text}")
    company.asaas_subscription_id = None
    company.payment_status = "cancelled"
    company.is_active = False
    company.blocked_at = datetime.now(timezone.utc)
    await db.commit()
    return {"cancelled": True}


# ── Webhook Asaas (público — chamado pelo Asaas, sem autenticação JWT) ─────────

@router.post(
    "/webhook",
    summary="Webhook Asaas — eventos de pagamento",
    include_in_schema=False,
)
async def webhook(request: Request, db: DbSession) -> dict:
    """
    Recebe eventos do Asaas e atualiza o status de pagamento das empresas.
    Eventos tratados:
      PAYMENT_RECEIVED  → ativa empresa
      PAYMENT_OVERDUE   → bloqueia empresa
      PAYMENT_DELETED   → bloqueia empresa
      PAYMENT_REFUNDED  → bloqueia empresa
    """
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Payload inválido.")

    event   = body.get("event", "")
    payment = body.get("payment", {})
    sub_id  = payment.get("subscription")

    logger.info("Asaas webhook: event=%s subscription=%s", event, sub_id)

    if not sub_id:
        return {"received": True}

    # Busca empresa pela subscription
    result = await db.execute(
        select(Company).where(Company.asaas_subscription_id == sub_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        logger.warning("Webhook: empresa não encontrada para subscription %s", sub_id)
        return {"received": True}

    if event == "PAYMENT_RECEIVED":
        company.payment_status = "active"
        company.is_active      = True
        company.blocked_at     = None
        next_due = payment.get("dueDate")
        if next_due:
            from datetime import date
            company.next_due_date = date.fromisoformat(next_due)
        logger.info("Empresa %s ATIVADA (pagamento recebido)", company.name)

    elif event in ("PAYMENT_OVERDUE", "PAYMENT_DELETED", "PAYMENT_REFUNDED"):
        company.payment_status = "overdue" if event == "PAYMENT_OVERDUE" else "suspended"
        company.is_active      = False
        company.blocked_at     = datetime.now(timezone.utc)
        logger.warning("Empresa %s BLOQUEADA — evento: %s", company.name, event)

    await db.commit()
    return {"received": True}
