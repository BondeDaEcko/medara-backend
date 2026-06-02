"""Pydantic schemas for billing endpoints."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


class CreateCustomerRequest(BaseModel):
    company_id: str
    cpf_cnpj:   str
    phone:      Optional[str] = None


class SubscribeRequest(BaseModel):
    company_id:    str
    plan:          str   # "essential" | "professional" | "gold"
    billing_type:  str = "PIX"   # PIX | BOLETO | CREDIT_CARD
    next_due_date: date

    @field_validator("plan")
    @classmethod
    def valid_plan(cls, v: str) -> str:
        allowed = {"essential", "professional", "gold"}
        if v not in allowed:
            raise ValueError(f"Plan must be one of {allowed}")
        return v


class BillingStatusResponse(BaseModel):
    company_id:            str
    payment_status:        str
    is_active:             bool
    asaas_customer_id:     Optional[str]
    asaas_subscription_id: Optional[str]
    next_due_date:         Optional[date]
    blocked_at:            Optional[str]


# Valores dos planos (R$)
PLAN_PRICES: dict[str, float] = {
    "essential":    290.0,
    "professional": 690.0,
    "gold":        1490.0,
}

PLAN_DESCRIPTIONS: dict[str, str] = {
    "essential":    "MEDARA Essencial — até 50 colaboradores",
    "professional": "MEDARA Profissional — até 200 colaboradores",
    "gold":         "MEDARA Gold — colaboradores ilimitados",
}
