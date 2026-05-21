"""MEDARA API — FastAPI application factory with lifespan, CORS, and security middleware."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.core.middleware import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.database import engine
from app.models import Base
from app.routers import auth, backup, companies, consultations, doctors, users

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("medara")

# ---------------------------------------------------------------------------
# Rate limiter global (slowapi)
# Limite geral: 200 req/min por IP
# Limite no login: 10 req/min (configurado no router auth.py)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up MEDARA API [env=%s]...", settings.environment)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured.")
    yield
    logger.info("Shutting down — disposing database engine.")
    await engine.dispose()


# ---------------------------------------------------------------------------
# Docs: visíveis apenas em desenvolvimento
# ---------------------------------------------------------------------------
_is_dev = settings.environment == "development"

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Backend da plataforma de saúde corporativa **MEDARA**.\n\n"
        "Autenticação via **Bearer JWT**. Inclua o header:\n"
        "`Authorization: Bearer <access_token>`"
    ),
    docs_url="/docs"     if _is_dev else None,
    redoc_url="/redoc"   if _is_dev else None,
    openapi_url="/openapi.json" if _is_dev else None,
    lifespan=lifespan,
)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Middlewares — ordem importa: o último adicionado é o primeiro a executar
# ---------------------------------------------------------------------------

# 1. Compressão gzip — respostas menores, mais rápidas
app.add_middleware(GZipMiddleware, minimum_size=500)

# 2. Limite de tamanho de requisição (padrão: 10 MB)
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_bytes=settings.max_request_body_mb * 1024 * 1024,
)

# 3. Headers de segurança OWASP em todas as respostas
app.add_middleware(SecurityHeadersMiddleware)

# 4. Trusted hosts — rejeita requests com Host header adulterado
#    Em produção, troque "*" pelo domínio real no .env: TRUSTED_HOSTS=["api.medara.com.br"]
if settings.trusted_hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

# 5. CORS — restringe origens permitidas
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"http://localhost(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global exception handler — nunca vaza stack trace para o cliente
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno do servidor. Tente novamente mais tarde."},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(companies.router)
app.include_router(doctors.router)
app.include_router(consultations.router)
app.include_router(backup.router)


# ---------------------------------------------------------------------------
# Health check (público — usado por Railway, Render, load balancers)
# ---------------------------------------------------------------------------
@app.get(
    "/health",
    tags=["system"],
    summary="Health check",
    include_in_schema=_is_dev,
)
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "MEDARA API", "version": settings.app_version}
