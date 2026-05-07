# Nexe Agent — Autonomous Business Agent

## Project Overview

AI-powered autonomous agent that accepts natural-language business goals, decomposes them into task plans, executes multi-step reasoning, and maintains immutable execution logs for full auditability.

## Current Status — RESUME HERE

**All 85 tasks implemented and golden path verified working.**
**Branch**: `1-autonomous-business-agent`
**Date paused**: 2026-05-04

### What works end-to-end
- Register / login (JWT)
- Submit a natural-language goal
- GPT-4o generates a task plan (real API call)
- Operator approves plan
- Celery executes all tasks via ReAct loop
- SSE live run monitor streams status
- Immutable log entries written to PostgreSQL
- GraphQL audit log viewer

### What is stub / not yet real
- `data_retrieval` handler — simulates fetching, no real web/API calls
- `content_generation` handler — calls GPT-4o but output goes nowhere (no publishing)
- `notification_dispatch` handler — no real SMTP configured, logs only

**Next logical work**: connect the three task handlers to real external services.

---

## How to Start the Stack

Prerequisites: Python 3.11+, Node.js 20+. No Docker needed — PostgreSQL and Redis run as hosted services (Neon + Upstash, configured in `.env`).

**1. Copy and fill in the env file**
```bash
cp .env.example .env
# Fill in DATABASE_URL, REDIS_URL, OPENAI_API_KEY, JWT_SECRET
```

**2. Backend API** (terminal 1)
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head        # first time only
uvicorn app.main:app --reload --port 8000
```

**3. Celery worker** (terminal 2)
```bash
cd backend
celery -A app.worker worker --loglevel=info
```

**4. Frontend** (terminal 3)
```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:3000

### URLs
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API docs | http://localhost:8000/docs |
| GraphQL | http://localhost:8000/graphql |

---

## Bugs Fixed in Session (2026-05-04) — DO NOT REINTRODUCE

| Bug | File fixed | What changed |
|-----|-----------|--------------|
| `email-validator` missing | `backend/requirements.txt` | Added `email-validator==2.2.0` |
| passlib incompatible with bcrypt 5 | `backend/app/services/auth_service.py` | Replaced passlib `CryptContext` with direct `bcrypt.hashpw/checkpw` calls |
| Celery task discovery broken | `backend/app/worker.py` | Replaced `autodiscover_tasks` with explicit `conf.include` list |
| `plan_goal` passed coroutine not string | `backend/app/tasks/plan_goal.py` | Added `await` to `_get_goal_text(...)` call |
| Alembic migration: duplicate enum types | `backend/alembic/versions/001_initial_schema.py` | Added `create_type=False` to all column ENUM definitions |
| No registration endpoint | `backend/app/routers/auth.py` | Added `POST /api/v1/auth/register` |
| Login page login-only | `frontend/src/app/login/page.tsx` | Added "Create account" tab |
| Goals page no auth guard | `frontend/src/app/goals/page.tsx` | Added redirect to `/login` when no token |

---

## Key Deviations from Original Spec

- **LLM**: OpenAI GPT-4o (not Anthropic Claude) — user confirmed `OPENAI_API_KEY` is the provider
- **Auth**: `bcrypt` used directly (not via passlib) due to bcrypt 5.x incompatibility

---

## Environment File

Create `.env` in project root (git-ignored):
```
OPENAI_API_KEY=sk-...your-key...
JWT_SECRET=any-long-random-string
POSTGRES_PASSWORD=nexe_dev
```

Generate JWT_SECRET: `python -c "import secrets; print(secrets.token_hex(32))"`

---

## SDD Artifacts (all under `specs/1-autonomous-business-agent/`)

| File | Purpose |
|------|---------|
| `spec.md` | Feature requirements |
| `plan.md` | Architecture plan |
| `data-model.md` | 7 DB tables, state machines |
| `contracts/rest-api.openapi.yaml` | OpenAPI 3.1 contract |
| `contracts/graphql.schema.graphql` | GraphQL schema |
| `tasks.md` | All 85 tasks — all marked [x] complete |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + FastAPI |
| Agent Reasoning | LangGraph + ReAct |
| LLM | **OpenAI GPT-4o** |
| Task Queue | Celery + Redis |
| Database | PostgreSQL 15 (append-only logs) |
| Real-time | Server-Sent Events (SSE) |
| Write API | REST/JSON |
| Audit Queries | GraphQL (Strawberry) |
| Frontend | Next.js 14 |
| Auth | JWT (access + refresh) via python-jose + bcrypt |
