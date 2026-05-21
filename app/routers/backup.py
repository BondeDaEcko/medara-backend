"""
MEDARA — Endpoint de backup manual do banco de dados.
Acessível apenas por admin e gestor (manager).
Retorna o arquivo .sql.gz como download direto.
"""

from __future__ import annotations

import gzip
import os
import subprocess
import tempfile
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.config import settings
from app.core.deps import require_manager_or_admin

router = APIRouter(prefix="/admin", tags=["admin"])


def _parse_db_params() -> dict[str, str]:
    """Extrai host, porta, usuário, senha e nome do banco da DATABASE_URL."""
    url = settings.database_url

    # SQLite em desenvolvimento: backup não faz sentido via pg_dump
    if url.startswith("sqlite"):
        return {}

    # postgresql+asyncpg://user:pass@host:port/dbname  →  parse normal
    clean = url.replace("+asyncpg", "").replace("+psycopg2", "")
    parsed = urlparse(clean)

    return {
        "host":     parsed.hostname or "localhost",
        "port":     str(parsed.port or 5432),
        "user":     parsed.username or "medara_user",
        "password": parsed.password or "",
        "dbname":   parsed.path.lstrip("/"),
    }


@router.post(
    "/backup",
    summary="Gerar backup manual do banco de dados",
    response_description="Arquivo .sql.gz para download",
    dependencies=[require_manager_or_admin()],
)
async def manual_backup():
    """
    Gera um dump completo do PostgreSQL e retorna como arquivo .sql.gz.
    Restrito a roles: admin e manager (gestor).
    """
    params = _parse_db_params()

    if not params:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Backup via API disponível apenas com PostgreSQL.",
        )

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"medara_backup_{timestamp}.sql.gz"

    # Arquivo temporário — removido após o download (BackgroundTask)
    tmp = tempfile.NamedTemporaryFile(suffix=".sql.gz", delete=False)
    tmp.close()

    env = os.environ.copy()
    env["PGPASSWORD"] = params["password"]

    result = subprocess.run(
        [
            "pg_dump",
            "-U", params["user"],
            "-h", params["host"],
            "-p", params["port"],
            "--no-owner",
            "--no-acl",
            params["dbname"],
        ],
        env=env,
        capture_output=True,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar backup: {stderr[:300]}",
        )

    with gzip.open(tmp.name, "wb") as f:
        f.write(result.stdout)

    def _cleanup():
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    return FileResponse(
        path=tmp.name,
        media_type="application/gzip",
        filename=filename,
        background=BackgroundTask(_cleanup),
    )
