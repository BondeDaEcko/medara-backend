"""
MEDARA — Middlewares de segurança customizados.

SecurityHeadersMiddleware  → headers OWASP + X-Request-ID para rastreabilidade
RequestSizeLimitMiddleware → rejeita requisições maiores que o limite configurado
"""

from __future__ import annotations
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injeta headers de segurança recomendados pela OWASP em todas as respostas.
    Protege contra: clickjacking, MIME sniffing, XSS, downgrade HTTPS.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Gera ID único por requisição — facilita rastrear ataques nos logs
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        # Impede que a API seja carregada em iframes (clickjacking)
        response.headers["X-Frame-Options"] = "DENY"

        # Navegador não deve "adivinhar" o tipo do conteúdo
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Força HTTPS por 1 ano (HSTS) — só ativo em produção
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # Política de referrer — não vaza URL interna em redirects
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restringe quais APIs do browser a página pode usar
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # Remove header que revela o framework usado
        response.headers.pop("server", None)
        response.headers.pop("x-powered-by", None)

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Rejeita requisições com body maior que max_bytes.
    Protege contra uploads maliciosos que tentam derrubar o servidor.
    """

    def __init__(self, app: ASGIApp, max_bytes: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            limit_mb = self.max_bytes // (1024 * 1024)
            return JSONResponse(
                status_code=413,
                content={"detail": f"Requisição muito grande. Limite: {limit_mb} MB."},
            )
        return await call_next(request)
