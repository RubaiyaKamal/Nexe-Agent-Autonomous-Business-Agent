# Tasks: Autonomous Business Agent

**Feature**: 1-autonomous-business-agent  
**Branch**: 1-autonomous-business-agent  
**Date**: 2026-05-04  
**Status**: In Progress — Phases 1–4 complete

---

## Implementation Strategy

Deliver working software in vertical slices — each phase is independently deployable and testable.

**MVP Scope** (Phases 1–4): A running API that accepts a goal, generates a plan, shows it to the operator, and awaits approval. Proves the full request/response loop before execution is wired.

**Full Scope**: Phases 5–9 add execution, failure handling, real-time streaming, audit queries, and the operator dashboard.

---

## User Story Map

| Story | Spec Scenario | Priority | Phase |
|-------|--------------|----------|-------|
| US1 | Scenario 1: Submit a Business Goal | P1 | Phase 3 |
| US5 | Scenario 5: Plan Review Before Execution | P1 | Phase 4 |
| US2 | Scenario 2: Multi-Step Reasoning Execution | P1 | Phase 5 |
| US4 | Scenario 4: Task Failure Handling | P2 | Phase 6 |
| US3 | Scenario 3: Execution Log Audit | P1 | Phase 7 |

---

## Phase 1: Setup

**Goal**: Skeleton project with infrastructure, config, and Docker ready to run.

- [x] T001 Create top-level project structure: `backend/`, `frontend/`, `docker-compose.yml`, `.env.example`, `README.md`
- [x] T002 Create `docker-compose.yml` with services: `postgres` (port 5432), `redis` (port 6379), `api` (port 8000), `worker`, `frontend` (port 3000)
- [x] T003 Create `.env.example` with all required variables: `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `JWT_SECRET`, `TASK_TIMEOUT_SECONDS=60`, `LOG_RETENTION_DAYS=90`, `AUTO_EXECUTE_DEFAULT=false`
- [x] T004 Create `backend/requirements.txt` pinning: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `alembic`, `asyncpg`, `celery[redis]`, `langgraph`, `openai`, `strawberry-graphql[fastapi]`, `pydantic`, `python-jose[cryptography]`, `passlib[bcrypt]`, `httpx`, `pytest`, `pytest-asyncio`
- [x] T005 Create `backend/app/__init__.py` and `backend/app/main.py` — FastAPI app instance, CORS middleware (restrict to frontend origin from env), lifespan handler for DB connection pool
- [x] T006 [P] Create `backend/app/config.py` — Pydantic `Settings` class loading all `.env` variables with validation; singleton via `lru_cache`
- [x] T007 [P] Create `backend/app/database.py` — SQLAlchemy async engine and session factory using `DATABASE_URL` from config; `get_session` dependency
- [x] T008 [P] Create `backend/app/worker.py` — Celery app configured with Redis broker and result backend from `REDIS_URL`; auto-discover tasks from `backend/app/tasks/`
- [x] T009 Scaffold `frontend/` as a Next.js 14 app with TypeScript: `package.json`, `tsconfig.json`, `src/app/layout.tsx`, `src/app/page.tsx`; install `axios`, `@apollo/client`, `graphql`, `tailwindcss`

---

## Phase 2: Foundational

**Goal**: All 7 database tables migrated, JWT auth working end-to-end. Blocks every user story.

- [x] T010 Create `backend/app/models/__init__.py` and `backend/app/models/user.py` — SQLAlchemy `User` model: `id` (UUID PK), `email` (unique), `display_name`, `hashed_password`, `auto_execute` (bool, default false), `created_at`, `last_login_at`
- [x] T011 [P] Create `backend/app/models/goal.py` — SQLAlchemy `Goal` model with `goal_status` enum (`received`, `planning`, `plan_ready`, `approved`, `executing`, `completed`, `cancelled`, `failed`); FK to users; `text` CHECK ≤ 2000 chars
- [x] T012 [P] Create `backend/app/models/plan.py` — SQLAlchemy `Plan` model with `plan_status` enum (`draft`, `approved`, `cancelled`); unique FK to goals; `task_count` CHECK (≥1 AND ≤20)
- [x] T013 [P] Create `backend/app/models/task.py` — SQLAlchemy `Task` model with `complexity_level` enum, `task_type` enum (`data_retrieval`, `content_generation`, `notification_dispatch`), `task_status` enum; `dependencies` as `ARRAY(UUID)`; `is_critical_path` bool; `order_index` int
- [x] T014 [P] Create `backend/app/models/execution_run.py` — SQLAlchemy `ExecutionRun` model with `run_status` enum; partial unique index `idx_runs_one_active_per_plan` on `(plan_id) WHERE status IN ('pending','running')`; counter columns (`tasks_total`, `tasks_succeeded`, `tasks_failed`, `tasks_skipped`)
- [x] T015 [P] Create `backend/app/models/log_entry.py` — SQLAlchemy `LogEntry` model with `log_status` enum; `input_snapshot` and `output_snapshot` as JSONB; `error_context` nullable; composite indexes per `data-model.md`
- [x] T016 [P] Create `backend/app/models/reasoning_trace.py` — SQLAlchemy `ReasoningTrace` model: `step_index`, `current_state` (JSONB), `decision`, `rationale`; composite index on `(run_id, task_id, step_index ASC)`
- [x] T017 Create `backend/alembic/` scaffold: `alembic.ini`, `alembic/env.py` using async SQLAlchemy engine; configure `target_metadata` from all models
- [x] T018 Create `backend/alembic/versions/001_initial_schema.py` — migration creating all 7 tables, all enums, all indexes, and the `app_writer` role with INSERT-only on `log_entries` (REVOKE UPDATE, DELETE)
- [x] T019 Create `backend/app/services/auth_service.py` — `hash_password`, `verify_password` (bcrypt), `create_access_token` (15-min JWT HS256), `create_refresh_token` (7-day), `decode_token`
- [x] T020 Create `backend/app/middleware/auth.py` — FastAPI dependency `require_current_user`: extracts and validates JWT from `Authorization: Bearer` header; raises 401 on missing/expired/invalid token
- [x] T021 Create `backend/app/schemas/auth.py` — Pydantic schemas: `TokenRequest`, `TokenResponse` (access_token, refresh_token, expires_in), `RefreshRequest`
- [x] T022 Create `backend/app/routers/auth.py` — `POST /api/v1/auth/token` and `POST /api/v1/auth/refresh` per OpenAPI contract; mount on FastAPI app in `main.py`

---

## Phase 3: US1 — Submit a Business Goal

**Story**: As a Business Operator, I submit a natural-language goal and receive confirmation that planning has begun, with the plan displayed within 5 seconds.

**Independent test criteria**: `POST /goals` returns HTTP 202 with a valid goal JSON. `GET /goals/{id}` returns updated status. After planning completes, `GET /goals/{id}/plan` returns a plan with ≥2 tasks, each having description, dependencies, and complexity.

- [x] T023 [US1] Create `backend/app/schemas/goal.py` — Pydantic schemas: `GoalCreate` (text: str, max_length=2000), `GoalResponse` (id, text, submitted_by, submitted_at, status)
- [x] T024 [P] [US1] Create `backend/app/services/goal_service.py` — `create_goal(text, user_id)` → inserts Goal row (status=received), returns GoalResponse; `get_goal(goal_id, user_id)` → returns GoalResponse; `update_goal_status(goal_id, status)`
- [x] T025 [P] [US1] Create `backend/app/routers/goals.py` — `POST /api/v1/goals`: validates GoalCreate, calls goal_service.create_goal, triggers background planning task, returns 202; `GET /api/v1/goals/{goal_id}`: returns GoalResponse; mount on app in `main.py`
- [x] T026 [US1] Create `backend/app/agent/dag_validator.py` — `validate_dag(tasks: list[TaskSpec]) -> None`: builds adjacency list from task dependencies, runs DFS cycle detection; raises `CircularDependencyError` with offending task IDs on cycle detection
- [x] T027 [US1] Create `backend/app/agent/planner.py` — `LangGraphPlanner` class: `async plan(goal_text: str) -> list[TaskSpec]` — constructs LangGraph graph with a single planning node that calls OpenAI GPT-4o with a structured system prompt instructing it to decompose the goal into 1–20 tasks as JSON; validates output against `TaskSpec` Pydantic schema; calls `validate_dag`; raises `PlanningError` if LLM output is unparseable or DAG is invalid
- [x] T028 [P] [US1] Create `backend/app/schemas/plan.py` — Pydantic schemas: `TaskSpec` (description, dependencies, complexity, type, is_critical_path, timeout_seconds), `PlanResponse` (id, goal_id, status, tasks: list[TaskSpec]), `TaskResponse`
- [x] T029 [US1] Create `backend/app/services/plan_service.py` — `create_plan(goal_id, tasks: list[TaskSpec])`: inserts Plan row (status=draft) and all Task rows with topological order_index; updates Goal status to `plan_ready`; `get_plan(goal_id)` → PlanResponse with tasks
- [x] T030 [US1] Create `backend/app/tasks/plan_goal.py` — Celery task `plan_goal_task(goal_id: str)`: updates goal status to `planning`, calls `LangGraphPlanner.plan`, calls `plan_service.create_plan`, updates goal status to `plan_ready`; on exception: updates goal status to `failed`, logs error

---

## Phase 4: US5 — Plan Review Before Execution

**Story**: As a Business Operator, I review the generated plan, then approve it to start execution or cancel it — no execution begins without my confirmation (unless auto-execute is enabled).

**Independent test criteria**: `GET /goals/{id}/plan` returns HTTP 200 with full task list when plan is ready, HTTP 202 when still planning. `POST /plan/approve` creates an ExecutionRun and returns 201. `POST /plan/cancel` transitions plan to cancelled and returns 200. Destructive operation guard prevents auto-execute from bypassing the gate.

- [x] T031 [US5] Create `backend/app/schemas/run.py` — Pydantic schemas: `ExecutionRunResponse` (id, plan_id, triggered_by, started_at, ended_at, status, auto_execute, tasks_total, tasks_succeeded, tasks_failed, tasks_skipped)
- [x] T032 [P] [US5] Add `GET /api/v1/goals/{goal_id}/plan` to `backend/app/routers/goals.py` — returns PlanResponse if plan exists and status ≥ plan_ready; returns HTTP 202 if goal status is `planning`; returns 404 if no plan exists
- [x] T033 [P] [US5] Add `POST /api/v1/goals/{goal_id}/plan/approve` to `backend/app/routers/goals.py` — guards: plan must be in `draft` status; no active run for this plan (409 if duplicate); calls `run_service.create_run`; returns 201 ExecutionRunResponse
- [x] T034 [P] [US5] Add `POST /api/v1/goals/{goal_id}/plan/cancel` to `backend/app/routers/goals.py` — transitions plan to `cancelled`, goal to `cancelled`; writes a run-level log entry (status=cancelled); returns updated PlanResponse
- [x] T035 [US5] Create `backend/app/services/run_service.py` — `create_run(plan_id, user_id, auto_execute: bool)`: inserts ExecutionRun (status=pending), enqueues `execute_run_task` Celery task; `get_run(run_id)` → ExecutionRunResponse; `cancel_run(run_id, user_id)` → sets status=cancelled, writes cancellation log entry
- [x] T036 [US5] Add auto-execute gate to `backend/app/routers/goals.py` `POST /plan/approve` — after plan is created, check `current_user.auto_execute`; if True AND plan contains no destructive tasks, automatically call `run_service.create_run`; if plan has destructive tasks, always require explicit approval regardless of auto_execute setting
- [x] T037 [US5] Create `backend/app/routers/runs.py` — `GET /api/v1/runs` (filtered list), `GET /api/v1/runs/{run_id}` (details), `POST /api/v1/runs/{run_id}/cancel`; mount on app in `main.py`

---

## Phase 5: US2 — Multi-Step Reasoning Execution

**Story**: As the Agent System, I execute tasks in dependency order, reason at each step, generate a trace, and adapt if a prior step produces unexpected output.

**Independent test criteria**: A 5-task plan with two dependency chains executes tasks strictly in topological order. Each completed task has a reasoning trace entry (step_index, decision, rationale). A plan with tasks T1→T2→T3 never starts T2 while T1 is in `queued` or `running` state.

- [x] T038 [US2] Create `backend/app/agent/scheduler.py` — `topological_sort(tasks: list[Task]) -> list[list[Task]]`: groups tasks into execution waves (tasks with no unmet dependencies are in the same wave, enabling parallel execution within a wave); raises `CircularDependencyError` if cycle detected at runtime
- [x] T039 [US2] Create `backend/app/agent/react_loop.py` — `ReActLoop` class: `async execute_task(task: Task, run_id: UUID, prior_outputs: dict) -> TaskResult`; builds LangGraph graph: observe node (reads task + prior outputs) → think node (Claude: generate reasoning + decision) → act node (calls appropriate handler) → evaluate node (validates output against task description); writes ReasoningTrace entry after think node; returns TaskResult
- [x] T040 [P] [US2] Create `backend/app/agent/handlers/data_retrieval.py` — `DataRetrievalHandler.execute(task: Task, context: dict) -> dict`: stub implementation that returns structured placeholder data; logs handler invocation; raises `HandlerError` on failure
- [x] T041 [P] [US2] Create `backend/app/agent/handlers/content_generation.py` — `ContentGenerationHandler.execute(task: Task, context: dict) -> dict`: calls Anthropic Claude API with task description and prior outputs as context; returns `{"content": "<generated text>"}` dict; respects task.timeout_seconds
- [x] T042 [P] [US2] Create `backend/app/agent/handlers/notification_dispatch.py` — `NotificationDispatchHandler.execute(task: Task, context: dict) -> dict`: stub email dispatch (logs to stdout in dev; configurable SMTP in prod via env); returns `{"dispatched": true, "recipients": [...]}` dict
- [x] T043 [US2] Create `backend/app/services/log_service.py` — `append_log_entry(run_id, task_id, status, reasoning_summary, input_snapshot, output_snapshot, error_context, retry_count) -> LogEntry`: INSERT-only; never updates or deletes; used by all components that write log entries
- [x] T044 [US2] Create `backend/app/services/trace_service.py` — `write_reasoning_trace(run_id, task_id, step_index, current_state, decision, rationale) -> ReasoningTrace`: inserts ReasoningTrace row; called by `ReActLoop` after think node
- [x] T045 [US2] Create `backend/app/tasks/execute_run.py` — Celery task `execute_run_task(run_id: str)`: loads run + plan + tasks; calls `topological_sort`; for each wave, appends log entry (status=queued) per task; iterates waves sequentially, tasks in each wave may run concurrently (Celery group); collects prior outputs; updates run summary counters; sets run status to `completed` or `failed`
- [x] T046 [US2] Wire task execution into `execute_run_task`: for each task in execution order — append log entry (running), call `ReActLoop.execute_task`, append log entry (succeeded/failed), update task status, update run counter columns

---

## Phase 6: US4 — Task Failure Handling

**Story**: As a Business Operator, when a task fails I see it in the log with full error context, the agent decides whether to retry/skip/halt, and I am notified of critical failures.

**Independent test criteria**: A simulated retriable failure retries exactly 3 times with increasing back-off before marking failed. A critical-path failure halts the run and writes a run-level log entry with status=failed. A non-critical failure writes a log entry with status=skipped and execution continues on remaining tasks.

- [x] T047 [US4] Create `backend/app/agent/failure_classifier.py` — `classify_failure(task: Task, error: Exception) -> FailureType` returning `Literal["retriable", "non_retriable", "critical_path"]`; critical_path if `task.is_critical_path=True`; retriable for transient errors (timeout, HTTP 5xx); non-retriable for all others
- [x] T048 [US4] Update `backend/app/tasks/execute_run.py` — wrap each task execution in retry loop: on failure, call `classify_failure`; if retriable and `retry_count < 3`: wait `2^retry_count` seconds, append log entry (status=retrying, retry_count=N), re-execute; if still failing after 3 retries: mark as non-retriable
- [x] T049 [US4] Update `backend/app/tasks/execute_run.py` — handle critical-path failure: set run status=failed, append run-level log entry (status=failed, reasoning_summary="Critical-path task failed: <task_id>"), call `notification_service.notify_operator(run_id, user_id, message)`, stop enqueuing further tasks
- [x] T050 [US4] Update `backend/app/tasks/execute_run.py` — handle non-critical failure: append log entry (status=skipped), increment `tasks_skipped` counter, continue execution of tasks not blocked by this task's output
- [x] T051 [P] [US4] Create `backend/app/services/notification_service.py` — `notify_operator(run_id, user_id, message: str)`: writes a run-level log entry of type notification; stub email send via SMTP config in env; logs to stdout in dev mode
- [x] T052 [US4] Handle ambiguous task output blocking downstream: in `ReActLoop.evaluate` node — if task output does not match any expected schema, emit `AmbiguousOutputEvent` to SSE channel (Phase 7), update run status to `pending_clarification`, halt further execution; add `POST /runs/{id}/clarify` stub endpoint returning 501 (deferred to Phase 2)

---

## Phase 7: US3 — Execution Log Audit

**Story**: As a Reviewer, I can open any completed or in-progress run and see a timestamped, ordered record of every task transition, reasoning, outcome, and error — and I can find any historical log within 10 seconds.

**Independent test criteria**: `GET /runs/{id}/logs` returns entries in timestamp order with no gaps. SSE stream delivers a `task_started` event within 1 second of the Celery worker updating task status. GraphQL `logs` query with `{ runId, status: FAILED }` filter returns only failed entries. `runAuditSummary` `totalLogEntries` equals the count of state transitions in the run.

- [x] T053 [US3] Create `backend/app/schemas/log.py` — Pydantic schemas: `LogEntryResponse` (id, run_id, task_id, timestamp, status, reasoning_summary, input_snapshot, output_snapshot, error_context, retry_count), `PaginatedLogs` (items, total)
- [x] T054 [P] [US3] Add `GET /api/v1/runs/{run_id}/logs` to `backend/app/routers/runs.py` — paginates log_entries by `(run_id, timestamp ASC)`; supports query params: `task_id`, `status`, `limit` (max 500), `offset`; returns `PaginatedLogs`
- [x] T055 [P] [US3] Add `GET /api/v1/runs` and `GET /api/v1/runs/{run_id}` to `backend/app/routers/runs.py` — full run list with status/date filters; single run detail with summary counters
- [x] T056 [US3] Create `backend/app/services/sse_service.py` — Redis pub/sub publisher: `publish_run_event(run_id, event_type, payload)` publishes JSON to channel `run:{run_id}`; subscriber `subscribe_run(run_id)` yields async generator of `RunStatusEvent` dicts
- [x] T057 [US3] Update `backend/app/tasks/execute_run.py` and `ReActLoop` — call `sse_service.publish_run_event` on every task state transition (queued, running, succeeded, failed, skipped, retrying, run_completed, run_failed, run_cancelled)
- [x] T058 [US3] Add `GET /api/v1/runs/{run_id}/status/stream` to `backend/app/routers/runs.py` — FastAPI `StreamingResponse` with `media_type="text/event-stream"`; subscribes to `sse_service.subscribe_run(run_id)`; formats each event as `data: <json>\n\n`; closes stream on terminal run status
- [x] T059 [US3] Create `backend/app/graphql/types.py` — Strawberry types mirroring GraphQL schema: `GoalType`, `PlanType`, `TaskType`, `ExecutionRunType`, `LogEntryType`, `ReasoningTraceType`, `RunAuditSummaryType`, `StatusCountType`, all input filters
- [x] T060 [US3] Create `backend/app/graphql/resolvers/log_resolvers.py` — async resolvers for: `logs(filter)`, `logEntry(id)`, `reasoningTraces(runId, taskId)`, `runAuditSummary(runId)` using `log_service` and `trace_service`
- [x] T061 [P] [US3] Create `backend/app/graphql/resolvers/run_resolvers.py` — async resolvers for: `run(id)`, `runs(filter)`, `goal(id)`, `goals(filter)` using `run_service` and `goal_service`
- [x] T062 [US3] Create `backend/app/graphql/schema.py` — Strawberry `Schema` combining all queries; mount on FastAPI at `/graphql` via `strawberry.fastapi.GraphQLRouter`; apply `require_current_user` dependency to all queries
- [x] T063 [US3] Create `backend/app/tasks/archive_logs.py` — Celery beat task `archive_old_logs` scheduled daily: moves `log_entries` rows where `timestamp < now() - 90 days` to an `archived_log_entries` table (same schema); does not delete; beat schedule configured in `worker.py`

---

## Phase 8: Operator Dashboard (Frontend)

**Goal**: Next.js operator dashboard covering all user stories end-to-end.

- [x] T064 Create `frontend/src/lib/api.ts` — Axios instance configured with base URL from env, JWT Authorization header interceptor (reads token from localStorage), 401 interceptor triggering token refresh
- [x] T065 [P] Create `frontend/src/lib/graphql.ts` — Apollo Client instance with HTTP link to `/graphql` endpoint and auth header; exports `client` singleton
- [x] T066 [P] Create `frontend/src/hooks/useAuth.ts` — React hook managing login state: `login(email, password)`, `logout()`, `refreshToken()`, `currentUser` derived from JWT payload
- [x] T067 [P] Create `frontend/src/app/login/page.tsx` — login form: email + password fields, calls `useAuth.login`, redirects to `/goals` on success, shows error message on 401
- [x] T068 [US1] Create `frontend/src/components/GoalForm.tsx` — textarea (max 2000 chars) with character counter, submit button; calls `POST /api/v1/goals`; navigates to `/goals/{id}/plan` after 202 response; shows validation error if text empty or over limit
- [x] T069 [US1] Create `frontend/src/app/goals/page.tsx` — goal list view: table of operator's submitted goals with status badges; "New Goal" button opens GoalForm
- [x] T070 [US5] Create `frontend/src/components/PlanReview.tsx` — displays plan tasks as ordered list with dependency arrows; shows complexity badge and task type per task; "Approve" and "Cancel" buttons calling respective API endpoints; disabled until `goal.status = plan_ready`; polls `GET /goals/{id}/plan` every 2s while status is `planning`
- [x] T071 [US5] Create `frontend/src/app/goals/[id]/plan/page.tsx` — mounts `PlanReview`; shows spinner while planning; redirects to `/goals/{id}/run/{runId}` after approve
- [x] T072 [US2] Create `frontend/src/hooks/useSSE.ts` — hook wrapping `EventSource`: `useSSE(url)` returns `{ events, status, error }`; auto-reconnects on close; parses JSON event data; closes EventSource when run reaches terminal status
- [x] T073 [US2] Create `frontend/src/components/RunMonitor.tsx` — live task progress view using `useSSE`; shows each task as a row with animated status indicator (queued → running → succeeded/failed/skipped); updates counters in real time; shows run summary on terminal status
- [x] T074 [US3] Create `frontend/src/components/LogViewer.tsx` — paginated log entry table: columns (timestamp, task, status, reasoning summary); expandable row showing input_snapshot, output_snapshot, error_context as formatted JSON; filter controls for status and date range (calls GraphQL `logs` query)
- [x] T075 [US3] Create `frontend/src/app/runs/[id]/logs/page.tsx` — mounts `LogViewer` for a given run; fetches `runAuditSummary` and shows at top (total, by status)
- [x] T076 [P] Create `frontend/src/app/settings/page.tsx` — operator settings: toggle for "Auto-execute mode" calling `PATCH /api/v1/users/me` (add endpoint stub to `backend/app/routers/users.py`); shows current value from JWT claims

---

## Phase 9: Polish & Cross-Cutting Concerns

**Goal**: Production-readiness: observability, security hardening, log integrity test, and developer documentation.

- [x] T077 Create `backend/app/routers/users.py` — `GET /api/v1/users/me` returns current user profile; `PATCH /api/v1/users/me` updates `auto_execute` setting; mount on app
- [x] T078 Add `GET /api/v1/health` to `backend/app/main.py` — returns `{"status": "ok", "db": "ok", "redis": "ok"}` by probing DB and Redis; no auth required; used by Docker Compose health checks
- [x] T079 Create `backend/tests/conftest.py` — pytest fixtures: async test DB (create/drop per test session), test JWT token, mock Anthropic client returning deterministic task lists
- [x] T080 [P] Create `backend/tests/test_log_integrity.py` — audit test verifying SC-04: run a full 5-task plan against test DB, count state transitions in code, assert `len(log_entries WHERE run_id=X) == expected_transition_count`; also assert no UPDATE or DELETE can be issued on `log_entries` table by app_writer role
- [x] T081 [P] Create `backend/tests/test_goals.py` — tests for: goal submission returns 202, goal text > 2000 chars returns 400, duplicate in-progress goal returns 409, unauthenticated request returns 401
- [x] T082 [P] Create `backend/tests/test_planner.py` — tests for: planner returns valid TaskSpec list, circular dependency raises error, LLM timeout raises PlanningError
- [x] T083 Add CORS config to `backend/app/main.py` — `CORSMiddleware` with `allow_origins=[settings.frontend_url]`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["Authorization","Content-Type"]`
- [x] T084 Add OpenTelemetry tracing to `backend/app/main.py` — `FastAPIInstrumentor`, `CeleryInstrumentor`; export to OTLP endpoint from env; add `trace_id` to log entry JSON output
- [x] T085 Create `README.md` at repo root — project overview, architecture diagram (ASCII), prerequisites, quickstart steps referencing `specs/1-autonomous-business-agent/quickstart.md`

---

## Dependency Graph

```
Phase 1 (Setup)
  └── Phase 2 (Foundational: DB + Auth)
        ├── Phase 3 (US1: Submit Goal)
        │     └── Phase 4 (US5: Plan Review)
        │           └── Phase 5 (US2: Execution)
        │                 ├── Phase 6 (US4: Failure Handling)
        │                 └── Phase 7 (US3: Log Audit)
        └── Phase 8 (Dashboard) ← depends on all API phases
              └── Phase 9 (Polish)
```

Stories with no cross-story dependencies (can develop UI in parallel with backend after Phase 2):
- Phase 8 UI tasks can begin after Phase 3 API is stable (mock backend for UI dev)
- Phase 6 and Phase 7 are independent of each other after Phase 5

---

## Parallel Execution Opportunities

### Within Phase 2 (after T010):
T011, T012, T013, T014, T015, T016 — each SQLAlchemy model file is independent; assign one per developer

### Within Phase 3 (after T023):
T024 (goal_service) and T025 (goals router) share only the schema — can be developed in parallel after T023

### Within Phase 5 (after T038, T039):
T040, T041, T042 — three task handlers, no dependencies on each other

### Within Phase 7 (after T059):
T060 and T061 — log resolvers and run resolvers are independent files

### Within Phase 8 (after T064, T065, T066):
T067, T068, T069, T076 — separate screens, no shared component dependencies

---

## Task Summary

| Phase | Tasks | Count |
|-------|-------|-------|
| Phase 1: Setup | T001–T009 | 9 |
| Phase 2: Foundational | T010–T022 | 13 |
| Phase 3: US1 Submit Goal | T023–T030 | 8 |
| Phase 4: US5 Plan Review | T031–T037 | 7 |
| Phase 5: US2 Multi-Step Reasoning | T038–T046 | 9 |
| Phase 6: US4 Failure Handling | T047–T052 | 6 |
| Phase 7: US3 Execution Log Audit | T053–T063 | 11 |
| Phase 8: Dashboard | T064–T076 | 13 |
| Phase 9: Polish | T077–T085 | 9 |
| **Total** | | **85** |

**Parallelizable tasks** ([P] labeled): 38 of 85  
**MVP scope** (Phases 1–4): T001–T037 — 37 tasks, independently deployable

---

## Independent Test Criteria Per Story

| Story | Pass Condition |
|-------|---------------|
| US1 (Submit Goal) | `POST /goals` → 202; `GET /goals/{id}/plan` returns ≥2 tasks with description + dependencies within 10s |
| US5 (Plan Review) | Approve returns 201 ExecutionRun; Cancel returns 200 cancelled Plan; auto-execute skipped for destructive tasks |
| US2 (Multi-Step Reasoning) | 5-task plan executes in topological order; ReasoningTrace per task; no out-of-order execution |
| US4 (Failure Handling) | Retriable failure retries ≤3 times; critical-path failure halts run; non-critical failure skipped |
| US3 (Log Audit) | SSE event within 1s of state change; GraphQL logs filter returns correct entries; audit summary counts match |
