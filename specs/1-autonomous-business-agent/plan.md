# Implementation Plan: Autonomous Business Agent

**Feature**: 1-autonomous-business-agent  
**Branch**: 1-autonomous-business-agent  
**Date**: 2026-05-04  
**Status**: Ready for Tasks

---

## Technical Context

| Item | Decision |
|------|----------|
| Backend framework | Python 3.11 + FastAPI (async-first, OpenAPI generation) |
| Agent reasoning | LangGraph + ReAct pattern |
| LLM | Anthropic Claude API (claude-sonnet-4-6 default) |
| Task queue | Celery + Redis |
| Database | PostgreSQL 15 |
| Real-time | Server-Sent Events (SSE) via FastAPI StreamingResponse |
| Write API | REST/JSON (OpenAPI spec in contracts/rest-api.openapi.yaml) |
| Audit query API | GraphQL via Strawberry (schema in contracts/graphql.schema.graphql) |
| Frontend | Next.js 14 (App Router) + React |
| Auth | JWT (access + refresh tokens) |
| ORM | SQLAlchemy 2.x (async) + Alembic migrations |
| Testing | pytest + pytest-asyncio (backend), Vitest + Playwright (frontend) |

---

## Constitution Check

| Principle | Satisfied? | How |
|-----------|-----------|-----|
| Transparency First | ✅ | Every task state transition writes a `log_entry` with `reasoning_summary` |
| Operator Control | ✅ | Default confirmation gate; `auto_execute` is opt-in per operator |
| Smallest Viable Change | ✅ | Phased delivery; each phase is independently deployable |
| Auditability | ✅ | `log_entries` table is append-only with DB-role-level enforcement |
| Fail Loud | ✅ | All failures logged; critical-path failures halt run and notify operator |
| No hardcoded secrets | ✅ | All secrets via `.env` / environment variables |
| Auth required | ✅ | JWT middleware on all operator-facing routes |
| Destructive gate | ✅ | Application guard regardless of `auto_execute` mode |

---

## Scope

### In Scope (MVP)
- Goal ingestion via REST API (FR-01)
- LangGraph-based task planning with DAG validation (FR-02)
- ReAct multi-step execution loop with reasoning traces (FR-03)
- Three task types: data_retrieval, content_generation, notification_dispatch (FR-04)
- Append-only execution log with full state snapshots (FR-05)
- Retry logic with exponential back-off (FR-06)
- Operator confirmation gate + auto-execute mode (FR-07)
- Real-time SSE status stream + run summary (FR-08)
- GraphQL audit query endpoint
- Operator dashboard (Next.js)
- JWT authentication

### Out of Scope (MVP)
- Third-party CRM/ERP integrations
- Multi-agent orchestration with external approval gates
- Billing and usage metering
- Mobile push notifications
- Additional task types beyond the three defined

---

## Delivery Phases

### Phase 1 — Foundation (Weeks 1–2)

**Goal**: Running API server with database, auth, and goal ingestion.

| Task | Deliverable |
|------|-------------|
| 1.1 | Project scaffold: FastAPI app, Alembic, Celery, Docker Compose |
| 1.2 | Database migrations: all 6 tables + append-only role enforcement |
| 1.3 | JWT auth: token issuance, refresh, middleware |
| 1.4 | POST /goals endpoint with validation |
| 1.5 | GET /goals/{id} endpoint |
| 1.6 | Unit tests for goal ingestion + auth |

**Acceptance gate**: `POST /goals` returns 202 with a valid goal JSON; auth rejects requests with missing/expired token.

---

### Phase 2 — Agent Planning (Weeks 3–4)

**Goal**: LangGraph planner decomposes goals into validated task DAGs.

| Task | Deliverable |
|------|-------------|
| 2.1 | LangGraph planner node: goal → task list with dependency graph |
| 2.2 | DAG circular-dependency validator |
| 2.3 | Plan persistence: POST /goals/{id}/plan (internal, triggered by planner) |
| 2.4 | GET /goals/{id}/plan endpoint |
| 2.5 | POST /goals/{id}/plan/approve and /cancel endpoints |
| 2.6 | Auto-execute mode: auto-approve if operator.auto_execute=true |
| 2.7 | Tests: planner output shape, circular dep detection, approval/cancel flows |

**Acceptance gate**: A submitted goal produces a plan with 2–20 tasks, each with correct dependency metadata, within 10 seconds.

---

### Phase 3 — Task Execution Engine (Weeks 5–7)

**Goal**: Celery workers execute plans in dependency order with full logging.

| Task | Deliverable |
|------|-------------|
| 3.1 | Celery worker setup + Redis broker |
| 3.2 | Task executor: data_retrieval handler |
| 3.3 | Task executor: content_generation handler (Claude API) |
| 3.4 | Task executor: notification_dispatch handler (email) |
| 3.5 | Dependency scheduler: topological sort → task queue order |
| 3.6 | ReAct step loop: per-task reasoning trace generation |
| 3.7 | Log entry writer: every state transition → append-only insert |
| 3.8 | Failure handler: categorize retriable / non-retriable / critical-path |
| 3.9 | Retry logic: up to 3 × exponential back-off |
| 3.10 | Run cancellation: signal Celery, log cancellation entry |
| 3.11 | Run summary update on completion |
| 3.12 | Integration tests: full run with mocked LLM, all task types |

**Acceptance gate**: A 5-task plan executes in dependency order; all state transitions appear in log_entries; one simulated failure triggers retry then logs correctly.

---

### Phase 4 — Real-Time & Audit API (Week 8)

**Goal**: SSE status stream and GraphQL audit queries.

| Task | Deliverable |
|------|-------------|
| 4.1 | SSE endpoint: GET /runs/{id}/status/stream |
| 4.2 | Redis pub/sub bridge: worker publishes events → SSE fan-out |
| 4.3 | GET /runs/{id}/logs endpoint with pagination |
| 4.4 | GraphQL endpoint (Strawberry): queries per graphql.schema.graphql |
| 4.5 | Log retention: archive job for entries > 90 days |
| 4.6 | Tests: SSE event delivery, GraphQL log queries, audit summary |

**Acceptance gate**: SSE delivers events within 1 second of task state change; GraphQL `logs` query with date-range filter returns correct entries within 10 seconds.

---

### Phase 5 — Operator Dashboard (Weeks 9–10)

**Goal**: Next.js frontend for goal submission, plan review, and log audit.

| Task | Deliverable |
|------|-------------|
| 5.1 | Auth screens: login, token refresh |
| 5.2 | Goal submission form with character counter |
| 5.3 | Plan review screen: task list, dependency view, approve/cancel actions |
| 5.4 | Run monitor screen: SSE-driven live task progress |
| 5.5 | Execution log viewer: filterable table, reasoning trace expand |
| 5.6 | Settings screen: toggle auto-execute mode |
| 5.7 | E2E Playwright tests: submit goal → approve → watch run → view logs |

**Acceptance gate**: E2E test passes the full golden path from goal submission to viewing the execution log.

---

## API Contract Summary

| Surface | Contract File |
|---------|--------------|
| REST (goals, runs, auth) | `contracts/rest-api.openapi.yaml` |
| GraphQL (audit logs) | `contracts/graphql.schema.graphql` |

---

## Data Model Summary

Full schema with all 6 tables, indexes, state machine transitions, and immutability constraints: `data-model.md`

---

## Key Interfaces

### LangGraph Planner Input/Output

```python
# Input
class PlannerInput(BaseModel):
    goal_id: UUID
    goal_text: str          # max 2000 chars

# Output
class PlannerOutput(BaseModel):
    tasks: list[TaskSpec]   # 1–20 items, validated DAG

class TaskSpec(BaseModel):
    description: str
    dependencies: list[UUID]
    complexity: Literal["low", "medium", "high"]
    type: Literal["data_retrieval", "content_generation", "notification_dispatch"]
    is_critical_path: bool
    timeout_seconds: int = 60
```

### Task Executor Interface

```python
class TaskResult(BaseModel):
    status: Literal["succeeded", "failed", "skipped"]
    output: dict
    reasoning_summary: str
    error_context: str | None = None
    failure_type: Literal["retriable", "non_retriable", "critical_path"] | None = None
```

### Log Entry Write (append-only)

```python
# Called on every task state transition — no updates, no deletes
async def append_log_entry(
    run_id: UUID,
    task_id: UUID | None,
    status: LogStatus,
    reasoning_summary: str,
    input_snapshot: dict,
    output_snapshot: dict,
    error_context: str | None = None,
    retry_count: int = 0,
) -> LogEntry: ...
```

---

## Non-Functional Requirements

| NFR | Budget | How |
|-----|--------|-----|
| Plan generation time | < 10s (FR-01) | Async LangGraph; LLM streaming |
| Run status updates | < 1s latency | SSE + Redis pub/sub |
| Log search (SC-05) | < 10s | Composite indexes on `log_entries` |
| 10-task run time | < 10 min (SC-03) | Celery parallel execution where deps allow |
| Log integrity | 100% transitions logged (SC-04) | Append after every state change, tested |
| Log retention | 90 days (spec constraint) | Nightly archive job |

---

## Security

| Control | Implementation |
|---------|---------------|
| Auth | JWT (HS256, 15-min access / 7-day refresh) |
| DB role | `app_writer`: INSERT-only on `log_entries`; no UPDATE/DELETE |
| Secrets | `.env` + environment variables; never committed |
| Input validation | Pydantic models on all API inputs |
| Destructive gate | Application-layer guard: always requires explicit confirmation |
| CORS | Restricted to operator dashboard origin |

---

## Observability

| Signal | What |
|--------|------|
| Structured logs | JSON logs on every request and task state change |
| Metrics | Run throughput, task success rate, LLM latency, queue depth |
| Traces | OpenTelemetry spans: API → Celery worker → LLM call |
| Alerts | Unhandled failure rate > 1% (SC-06); queue depth > 100; LLM error rate > 5% |

---

## Risks

| Risk | Blast Radius | Mitigation |
|------|-------------|-----------|
| LLM produces invalid task DAG (circular deps) | Plan rejected silently | DAG validator + user-facing error message; retry planning with clarification prompt |
| Celery worker crash mid-task | Lost log entry, orphaned run | Celery task idempotency key + heartbeat; run watchdog marks stale runs failed |
| Log table grows unbounded | Query degradation (SC-05) | Composite indexes + 90-day archive job; test with 1M row fixture |
