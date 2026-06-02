"""Asaas API client — thin async wrapper around httpx."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("medara.asaas")

_HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "access_token": settings.asaas_api_key,
}


async def _request(method: str, path: str, **kwargs: Any) -> dict:
    url = f"{settings.asaas_base_url}{path}"
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.request(method, url, headers=_HEADERS, **kwargs)
    if resp.status_code >= 400:
        logger.error("Asaas %s %s → %s: %s", method, path, resp.status_code, resp.text)
        resp.raise_for_status()
    return resp.json()


# ── Customers ────────────────────────────────────────────────────────────────

async def create_customer(
    name: str,
    email: str,
    cpf_cnpj: str,
    phone: str | None = None,
) -> dict:
    return await _request("POST", "/customers", json={
        "name":    name,
        "email":   email,
        "cpfCnpj": cpf_cnpj,
        "phone":   phone,
        "notificationDisabled": False,
    })


async def get_customer(customer_id: str) -> dict:
    return await _request("GET", f"/customers/{customer_id}")


# ── Subscriptions ─────────────────────────────────────────────────────────────

CYCLE_MONTHLY = "MONTHLY"

async def create_subscription(
    customer_id: str,
    value: float,
    next_due_date: str,           # "YYYY-MM-DD"
    description: str = "Plano MEDARA",
    billing_type: str = "BOLETO", # BOLETO | PIX | CREDIT_CARD
) -> dict:
    return await _request("POST", "/subscriptions", json={
        "customer":     customer_id,
        "billingType":  billing_type,
        "value":        value,
        "nextDueDate":  next_due_date,
        "cycle":        CYCLE_MONTHLY,
        "description":  description,
    })


async def cancel_subscription(subscription_id: str) -> dict:
    return await _request("DELETE", f"/subscriptions/{subscription_id}")


async def get_subscription(subscription_id: str) -> dict:
    return await _request("GET", f"/subscriptions/{subscription_id}")


# ── Payments ──────────────────────────────────────────────────────────────────

async def list_payments(subscription_id: str) -> dict:
    return await _request("GET", "/payments", params={
        "subscription": subscription_id,
    })
