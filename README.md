# MEDARA API

Backend da plataforma de saúde corporativa **MEDARA** — Fase 1.

## Stack

- **FastAPI** 0.115 + **Uvicorn**
- **SQLAlchemy 2.0** async com **aiosqlite** (dev) / PostgreSQL (produção)
- **Alembic** para migrations
- **JWT** via python-jose + passlib/bcrypt
- **Pydantic V2** para validação
- **slowapi** para rate limiting

---

## Instalacao

```bash
# 1. Criar ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variaveis de ambiente
copy .env.example .env
# Edite .env com suas configuracoes
```

---

## Rodar localmente

```bash
uvicorn app.main:app --reload
```

A API sobe em `http://localhost:8000`.
Documentacao interativa: `http://localhost:8000/docs`

---

## Migrations com Alembic

```bash
# Gerar nova migration a partir dos models
alembic revision --autogenerate -m "descricao da mudanca"

# Aplicar migrations pendentes
alembic upgrade head

# Reverter ultima migration
alembic downgrade -1

# Ver historico de migrations
alembic history
```

> Em desenvolvimento com SQLite, as tabelas sao criadas automaticamente no startup via `Base.metadata.create_all`. Para producao com PostgreSQL, use Alembic.

---

## Variaveis de Ambiente

| Variavel | Descricao | Padrao |
|---|---|---|
| `DATABASE_URL` | URL do banco de dados | `sqlite+aiosqlite:///./medara.db` |
| `SECRET_KEY` | Chave secreta para JWT (min 32 chars) | (obrigatorio em producao) |
| `ALGORITHM` | Algoritmo JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiracao do access token | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Expiracao do refresh token | `7` |
| `CORS_ORIGINS` | Lista JSON de origens permitidas | `[...]` |

Para producao com PostgreSQL:
```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/medara
```

---

## Endpoints Principais

### Auth

#### POST /auth/register
Registrar novo funcionario.
```json
// Request
{
  "email": "joao@techcorp.com.br",
  "password": "senha123",
  "full_name": "Joao Silva",
  "company_id": "uuid-da-empresa"
}
// Response 201
{
  "id": "uuid",
  "email": "joao@techcorp.com.br",
  "full_name": "Joao Silva",
  "role": "employee",
  "avatar_initials": "JS",
  ...
}
```

#### POST /auth/login
```json
// Request
{ "email": "joao@techcorp.com.br", "password": "senha123" }
// Response 200
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

#### POST /auth/refresh
```json
// Request
{ "refresh_token": "eyJ..." }
// Response 200
{ "access_token": "eyJ...", "token_type": "bearer" }
```

#### POST /auth/logout
Requer `Authorization: Bearer <access_token>`.
```json
// Request
{ "refresh_token": "eyJ..." }
// Response 204 No Content
```

#### GET /auth/me
Requer `Authorization: Bearer <access_token>`.

---

### Users

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| GET | `/users/me` | Todos | Perfil completo com empresa |
| PUT | `/users/me` | Todos | Atualizar nome/avatar |
| GET | `/users/{id}` | manager, admin | Buscar usuario por ID |

---

### Companies

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| POST | `/companies` | admin | Criar empresa |
| GET | `/companies/{id}` | Todos* | Dados da empresa |
| GET | `/companies/{id}/users` | manager, admin | Listar funcionarios |
| POST | `/companies/{id}/invite` | manager, admin | Convidar funcionario |

*Employees so podem ver a propria empresa.

#### POST /companies
```json
// Request (admin)
{
  "name": "TechCorp",
  "domain": "techcorp.com.br",
  "plan": "professional"
}
```

---

### Doctors

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| POST | `/doctors/register` | doctor | Criar perfil medico |
| GET | `/doctors` | Todos | Listar medicos (com filtros) |
| GET | `/doctors/{id}` | Todos | Perfil do medico |
| PATCH | `/doctors/me/availability` | doctor | Ativar/desativar disponibilidade |

#### GET /doctors — Query params
- `specialty_id`: UUID da especialidade para filtrar
- `available_only`: `true` para apenas medicos disponiveis agora
- `limit`: max resultados (padrao: 20, max: 100)
- `offset`: paginacao

#### POST /doctors/register
```json
// Request (usuario com role=doctor)
{
  "crm": "123456",
  "crm_state": "SP",
  "bio": "Medico clinico geral com 10 anos de experiencia.",
  "specialty_ids": ["uuid-especialidade-1"]
}
```

#### PATCH /doctors/me/availability
```json
{ "is_available": true }
```

---

## Health Check

```
GET /health
Response: { "status": "ok", "service": "MEDARA API", "version": "1.0.0" }
```

---

## Deploy no Railway

### Pre-requisitos
1. Conta no [Railway](https://railway.app)
2. Banco PostgreSQL provisionado no Railway

### Passos

```bash
# 1. Instalar Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Criar projeto
railway init

# 4. Configurar variaveis de ambiente no painel Railway:
#    DATABASE_URL  (copiada da aba PostgreSQL > Connect)
#    SECRET_KEY    (gere com: python -c "import secrets; print(secrets.token_hex(32))")
#    CORS_ORIGINS  ["https://medara-web.vercel.app"]

# 5. Deploy
railway up
```

O `railway.toml` ja esta configurado com o health check em `/health`.

### Migracoes em producao
```bash
# Conectar ao servico e rodar migrations
railway run alembic upgrade head
```

---

## Estrutura de Diretorios

```
medara-backend/
├── app/
│   ├── main.py          # Aplicacao FastAPI, CORS, lifespan
│   ├── config.py        # Configuracoes via pydantic-settings
│   ├── database.py      # Engine async, session factory
│   ├── models/          # ORM: User, Company, Doctor, Consultation
│   ├── schemas/         # Pydantic V2: request/response
│   ├── routers/         # Endpoints: auth, users, companies, doctors
│   └── core/
│       ├── security.py  # bcrypt, JWT
│       └── deps.py      # Dependencias FastAPI (auth, roles)
├── alembic/             # Migrations
├── Dockerfile
├── railway.toml
└── requirements.txt
```
