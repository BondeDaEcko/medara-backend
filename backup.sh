#!/bin/bash
# =============================================================
#  MEDARA — Script de backup automático do PostgreSQL
#  Rodado pelo cron todo dia às 02:00
#  Guarda os últimos 30 dias e loga tudo em /var/log/medara_backup.log
# =============================================================

set -euo pipefail

# ── Configurações ─────────────────────────────────────────────
DB_NAME="${POSTGRES_DB:-medara_db}"
DB_USER="${POSTGRES_USER:-medara_user}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_PASSWORD="${POSTGRES_PASSWORD}"          # vem da variável de ambiente

BACKUP_DIR="/var/backups/medara"
LOG_FILE="/var/log/medara_backup.log"
KEEP_DAYS=30

DATE=$(date +"%Y-%m-%d_%H-%M-%S")
FILENAME="medara_${DATE}.sql.gz"
FILEPATH="$BACKUP_DIR/$FILENAME"

# ── Prepara pasta ─────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Iniciando backup: $FILENAME"

# ── Dump + compressão ─────────────────────────────────────────
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -U "$DB_USER" \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    --no-owner \
    --no-acl \
    "$DB_NAME" | gzip > "$FILEPATH"

BACKUP_SIZE=$(du -sh "$FILEPATH" | cut -f1)
log "Backup criado com sucesso: $FILENAME ($BACKUP_SIZE)"

# ── Remove backups com mais de 30 dias ────────────────────────
DELETED=$(find "$BACKUP_DIR" -name "medara_*.sql.gz" -mtime +$KEEP_DAYS -print -delete | wc -l)
if [ "$DELETED" -gt 0 ]; then
    log "Backups antigos removidos: $DELETED arquivo(s)"
fi

log "Backups disponíveis em $BACKUP_DIR:"
ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null | awk '{print "  " $NF " — " $5}' | tee -a "$LOG_FILE"

log "Backup concluído."
