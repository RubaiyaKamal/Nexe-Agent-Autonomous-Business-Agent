# Quickstart: Autonomous Business Agent

**Feature**: 1-autonomous-business-agent  
**Date**: 2026-05-04

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 20+ |
| Docker + Docker Compose | Latest stable |
| PostgreSQL | 15+ (via Docker) |
| Redis | 7+ (via Docker) |

---

## 1. Clone & Configure

```bash
git clone <repo-url>
cd nexe-agent
cp .env.example .env
```

Edit `.env` and set:

```env
# Required
DATABASE_URL=postgresql://nexe:nexe@localhost:5432/nexe_agent
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=<your-claude-api-key>
JWT_SECRET=<random-256-bit-secret>

# Optional (defaults shown)
TASK_TIMEOUT_SECONDS=60
LOG_RETENTION_DAYS=90
AUTO_EXECUTE_DEFAULT=false
```

---

## 2. Start Infrastructure

```bash
docker compose up -d postgres redis
```

Verify:
```bash
docker compose ps   # both services should show "healthy"
```

---

## 3. Run Database Migrations

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

This creates all tables including the append-only `log_entries` table and applies the INSERT-only role restriction.

---

## 4. Start the Backend

```bash
# Terminal 1 — FastAPI API server
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Celery worker (task execution)
celery -A app.worker worker --loglevel=info --concurrency=4
```

API docs available at: `http://localhost:8000/docs`

---

## 5. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Operator dashboard at: `http://localhost:3000`

---

## 6. Submit Your First Goal

```bash
# Get a token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"changeme"}' \
  | jq -r '.access_token')

# Submit a goal
curl -X POST http://localhost:8000/api/v1/goals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Generate a weekly sales summary and send it to the leadership team"}'
```

Expected response (HTTP 202):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "text": "Generate a weekly sales summary and send it to the leadership team",
  "status": "planning",
  "submitted_at": "2026-05-04T10:00:00Z"
}
```

---

## 7. Review and Approve the Plan

```bash
# Poll until plan_ready (or use the dashboard)
curl http://localhost:8000/api/v1/goals/<goal-id>/plan \
  -H "Authorization: Bearer $TOKEN"

# Approve the plan
curl -X POST http://localhost:8000/api/v1/goals/<goal-id>/plan/approve \
  -H "Authorization: Bearer $TOKEN"
```

---

## 8. Watch Execution in Real Time

```bash
# Subscribe to SSE stream
curl -N http://localhost:8000/api/v1/runs/<run-id>/status/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: text/event-stream"
```

---

## 9. Query the Execution Log

```graphql
# POST http://localhost:8000/graphql
query AuditRun {
  logs(filter: { runId: "<run-id>", limit: 50 }) {
    nodes {
      timestamp
      status
      reasoningSummary
      task { description }
      errorContext
    }
    pageInfo { totalCount }
  }
}
```

---

## Architecture Overview

```
Operator (Browser)
    │
    ├── REST API (FastAPI :8000)
    │     ├── POST /goals           → creates Goal, triggers LangGraph planning
    │     ├── POST /plan/approve    → creates ExecutionRun, enqueues Celery tasks
    │     ├── GET  /runs/.../stream → SSE real-time status
    │     └── GET  /runs/.../logs   → log entries
    │
    ├── GraphQL API (/graphql)
    │     └── Flexible audit log queries
    │
    ├── Celery Worker
    │     ├── Pulls tasks from Redis queue
    │     ├── Executes: data_retrieval | content_generation | notification_dispatch
    │     ├── Writes log entries (append-only) after each state transition
    │     └── Retries retriable failures (≤3 × exponential back-off)
    │
    └── LangGraph Agent
          ├── ReAct loop: reason → tool-call → observe → repeat
          ├── Generates reasoning trace per step
          └── Calls Anthropic Claude API for reasoning
```

---

## Running Tests

```bash
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing

cd frontend
npm test
```

Log integrity test verifies SC-04 (100% log entry coverage):
```bash
pytest tests/test_log_integrity.py -v
```
