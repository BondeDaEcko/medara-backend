# MEDARA — Backend (FastAPI)

## O que é
API REST da plataforma de saúde corporativa MEDARA. Autenticação JWT, controle de acesso por role, videochamadas, backup automatizado.

## Stack
- Python + FastAPI + SQLAlchemy 2.0 async
- Banco: SQLite (dev) / PostgreSQL (produção)
- Auth: JWT (access 30min + refresh 7 dias) + bcrypt
- Deploy: Railway ou servidor VPS

## Rodar localmente
```
cd C:\Users\Alvaro\medara-backend
.venv\Scripts\activate
uvicorn app.main:app --reload
# Docs: http://localhost:8000/docs (só em development)
```

## Seed de dados de teste
```
python seed.py
```
Cria: empresa Leal Castro, admin, gestor, funcionários, médicos.

## Credenciais de teste (após seed)
| Email | Senha | Role |
|---|---|---|
| admin@medara.com.br | Admin@123 | admin |
| rh@techcorp.com.br | Gestor@123 | manager |
| maria@techcorp.com.br | Func@123 | employee |
| dr.rafael@medara.com.br | Doctor@123 | doctor |

## Variáveis de ambiente (.env)
```
DATABASE_URL=postgresql+asyncpg://user:pass@host/medara_db
SECRET_KEY=chave-super-secreta-minimo-32-chars
ENVIRONMENT=production
AGORA_APP_ID=seu-app-id-do-agora
AGORA_APP_CERTIFICATE=seu-certificate
```

## Estrutura
```
app/
  main.py          — FastAPI app + middlewares de segurança
  config.py        — Settings via pydantic-settings
  database.py      — Engine async SQLAlchemy
  models/          — User, Company, Doctor, Specialty, Consultation, RefreshToken
  routers/
    auth.py        — login, register, refresh, logout, me
    users.py       — perfil, atualização
    companies.py   — gestão de empresas
    doctors.py     — médicos e especialidades
    consultations.py — token Agora para videochamadas
    backup.py      — backup manual do banco (role: manager/admin)
  schemas/         — Pydantic schemas de validação
  core/
    security.py    — bcrypt, JWT
    deps.py        — get_current_user, require_roles, RBAC
    middleware.py  — SecurityHeaders, RequestSizeLimit, X-Request-ID
```

## Middlewares de segurança (em ordem)
1. GZipMiddleware
2. RequestSizeLimitMiddleware (10MB)
3. SecurityHeadersMiddleware (OWASP headers + X-Request-ID)
4. TrustedHostMiddleware (quando configurado)
5. CORSMiddleware

## Rate limiting
- Global: 200 req/min por IP
- Login: 10 req/min por IP (anti brute-force)

## Backup
- Automático: cron às 22h (ver backup.sh + backup_cron.txt)
- Manual: POST /admin/backup (role: manager/admin) → baixa .sql.gz
- Retenção: 30 dias

## Videochamadas
- POST /consultations/token → retorna channel + token Agora
- Requer AGORA_APP_ID configurado no .env
- Em modo dev (sem App ID): retorna 503 com instruções

## Push para GitHub
```
cd C:\Users\Alvaro\medara-backend
git add .
git commit -m "descrição"
git push
```
Repo: https://github.com/BondeDaEcko/medara-backend

## Pendências principais
- [ ] Conectar frontend ao backend (substituir TEST_USERS)
- [ ] Alembic migrations (trocar create_all por migrations versionadas)
- [ ] Deploy em servidor de produção (Railway ou VPS)
- [ ] Endpoint de prontuário eletrônico
- [ ] Integração Memed (receitas digitais)
- [ ] WebSocket para notificações em tempo real
- [ ] 2FA por SMS/email
- [ ] Audit log de todas as ações
