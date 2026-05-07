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

- Python 3.11+
- Node.js 20+
- A [Neon](https://neon.tech) PostgreSQL database (free tier)
- An [Upstash](https://upstash.com) Redis database (free tier)
- OpenAI API key

## Quick Start

```bash
cp .env.example .env
# Edit .env — fill in DATABASE_URL, REDIS_URL, OPENAI_API_KEY, JWT_SECRET
```

**Terminal 1 — API**
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head      # first time only
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Celery worker**
```bash
cd backend
celery -A app.worker worker --loglevel=info
```

**Terminal 3 — Frontend**
```bash
cd frontend
npm install
npm run dev
```

API: http://localhost:8000/docs  
Frontend: http://localhost:3000  
GraphQL playground: http://localhost:8000/graphql

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
