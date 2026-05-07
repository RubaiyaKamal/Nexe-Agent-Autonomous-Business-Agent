# Nexe Agent — Autonomous Business Agent

AI-powered agent that accepts natural-language business goals, decomposes them into task plans, executes multi-step reasoning, and maintains immutable execution logs.

## Architecture

```
 Operator (browser)
       │  HTTP/REST + GraphQL + SSE
       ▼
  FastAPI (port 8000)
  ├── POST /api/v1/goals          ← submit goal
  ├── GET  /api/v1/goals/{id}/plan ← review plan
  ├── POST /goals/{id}/plan/approve ← trigger run
  ├── GET  /api/v1/runs/{id}/status/stream  ← SSE live updates
  ├── GET  /api/v1/runs/{id}/logs  ← paginated log entries
  └── /graphql                    ← Strawberry GraphQL audit queries
       │
       ├── PostgreSQL 15 (append-only log_entries)
       ├── Redis (Celery broker + SSE pub/sub)
       └── Celery Worker
             ├── plan_goal_task  → LangGraph + GPT-4o planner
             └── execute_run_task → ReAct loop (observe→think→act→evaluate)

  Next.js 14 (port 3000)
  ├── /goals          — goal list + submission
  ├── /goals/{id}/plan — plan review + approve/cancel
  ├── /goals/{id}/run/{runId} — live run monitor (SSE)
  ├── /runs/{id}/logs — execution log viewer (GraphQL)
  └── /settings       — auto-execute toggle
```

## Prerequisites

- Docker + Docker Compose
- OpenAI API key

## Quick Start

```bash
cp .env.example .env
# Edit .env — set OPENAI_API_KEY and JWT_SECRET

docker compose up --build

# In another terminal, run DB migration
docker compose exec api alembic upgrade head
```

API: http://localhost:8000/docs  
Frontend: http://localhost:3000  
GraphQL playground: http://localhost:8000/graphql

## Local Development (without Docker)

```bash
# Backend
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Worker (separate terminal)
celery -A app.worker worker --loglevel=info

# Frontend
cd frontend
npm install
npm run dev
```

## Running Tests

```bash
cd backend
pytest tests/ -v
```

## Full Documentation

See `specs/1-autonomous-business-agent/` for:
- `spec.md` — feature requirements
- `plan.md` — architecture decisions
- `data-model.md` — database schema
- `quickstart.md` — first-goal walkthrough
