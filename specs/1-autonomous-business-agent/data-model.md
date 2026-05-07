# Data Model: Autonomous Business Agent

**Feature**: 1-autonomous-business-agent  
**Date**: 2026-05-04  
**Status**: Final

---

## Overview

Six core entities map directly to the spec's Key Entities section. PostgreSQL is the persistence layer. The `log_entries` table is append-only — the application database role has INSERT-only permission (no UPDATE or DELETE) to enforce immutability (FR-05, Constitution: Auditability).

---

## Entity Relationship Diagram

```
users
  └── goals (submitted_by → users.id)
        └── plans (goal_id → goals.id)
              └── tasks (plan_id → plans.id)
                    └── tasks.dependencies[] → tasks.id
              └── execution_runs (plan_id → plans.id, triggered_by → users.id)
                    └── log_entries (run_id → execution_runs.id, task_id → tasks.id)
                    └── reasoning_traces (run_id → execution_runs.id, task_id → tasks.id)
```

---

## Table Definitions

### `users`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, NOT NULL | Generated |
| email | TEXT | UNIQUE, NOT NULL | Primary identifier |
| display_name | TEXT | NOT NULL | |
| auto_execute | BOOLEAN | NOT NULL, DEFAULT false | Per-operator opt-in |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| last_login_at | TIMESTAMPTZ | | |

---

### `goals`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, NOT NULL | Generated |
| text | TEXT | NOT NULL, CHECK(length ≤ 2000) | Natural language goal |
| submitted_by | UUID | FK → users.id, NOT NULL | |
| submitted_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| status | goal_status | NOT NULL, DEFAULT 'received' | See enum below |

**`goal_status` enum**: `received` → `planning` → `plan_ready` → `approved` → `executing` → `completed` \| `cancelled` \| `failed`

**Indexes**:
- `idx_goals_submitted_by` on `(submitted_by, submitted_at DESC)`
- `idx_goals_status` on `(status)`

---

### `plans`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, NOT NULL | Generated |
| goal_id | UUID | FK → goals.id, NOT NULL, UNIQUE | One plan per goal |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| status | plan_status | NOT NULL, DEFAULT 'draft' | See enum below |
| task_count | INT | NOT NULL, CHECK(≥1 AND ≤20) | Enforces FR-02 |

**`plan_status` enum**: `draft` \| `approved` \| `cancelled`

**Indexes**:
- `idx_plans_goal_id` on `(goal_id)`
- `idx_plans_status` on `(status)`

---

### `tasks`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, NOT NULL | Generated |
| plan_id | UUID | FK → plans.id, NOT NULL | |
| description | TEXT | NOT NULL | Human-readable |
| dependencies | UUID[] | NOT NULL, DEFAULT '{}' | Task IDs this task waits for |
| complexity | complexity_level | NOT NULL | `low` \| `medium` \| `high` |
| type | task_type | NOT NULL | See enum below |
| timeout_seconds | INT | NOT NULL, DEFAULT 60 | FR-04 configurable timeout |
| order_index | INT | NOT NULL | Topological sort position |
| status | task_status | NOT NULL, DEFAULT 'queued' | See enum below |
| is_critical_path | BOOLEAN | NOT NULL, DEFAULT false | FR-06 failure routing |

**`task_type` enum**: `data_retrieval` \| `content_generation` \| `notification_dispatch`

**`task_status` enum**: `queued` \| `running` \| `succeeded` \| `failed` \| `skipped` \| `cancelled`

**Constraints**:
- Circular dependency check: enforced at plan-generation time (application layer validates DAG before inserting)

**Indexes**:
- `idx_tasks_plan_id` on `(plan_id, order_index)`
- `idx_tasks_status` on `(status)`

---

### `execution_runs`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, NOT NULL | Generated |
| plan_id | UUID | FK → plans.id, NOT NULL | |
| triggered_by | UUID | FK → users.id, NOT NULL | |
| started_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| ended_at | TIMESTAMPTZ | | NULL until complete |
| status | run_status | NOT NULL, DEFAULT 'pending' | See enum below |
| auto_execute | BOOLEAN | NOT NULL | Snapshot of operator setting at run time |
| tasks_total | INT | NOT NULL, DEFAULT 0 | FR-08 summary |
| tasks_succeeded | INT | NOT NULL, DEFAULT 0 | |
| tasks_failed | INT | NOT NULL, DEFAULT 0 | |
| tasks_skipped | INT | NOT NULL, DEFAULT 0 | |

**`run_status` enum**: `pending` \| `running` \| `completed` \| `failed` \| `cancelled`

**Constraint**: Only one active run per plan at a time — enforced via partial unique index:
```sql
CREATE UNIQUE INDEX idx_runs_one_active_per_plan
  ON execution_runs (plan_id)
  WHERE status IN ('pending', 'running');
```

**Indexes**:
- `idx_runs_plan_id` on `(plan_id, started_at DESC)`
- `idx_runs_triggered_by` on `(triggered_by, started_at DESC)`
- `idx_runs_status` on `(status)`

---

### `log_entries` ⚠ APPEND-ONLY

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, NOT NULL | Generated |
| run_id | UUID | FK → execution_runs.id, NOT NULL | |
| task_id | UUID | FK → tasks.id | NULL for run-level events |
| timestamp | TIMESTAMPTZ | NOT NULL, DEFAULT now() | ISO 8601 (FR-05) |
| status | log_status | NOT NULL | See enum below |
| reasoning_summary | TEXT | NOT NULL | Agent's stated rationale |
| input_snapshot | JSONB | NOT NULL, DEFAULT '{}' | State entering this step |
| output_snapshot | JSONB | NOT NULL, DEFAULT '{}' | State produced by this step |
| error_context | TEXT | | NULL on success |
| retry_count | INT | NOT NULL, DEFAULT 0 | Current attempt number |

**`log_status` enum**: `queued` \| `running` \| `succeeded` \| `failed` \| `skipped` \| `cancelled` \| `retrying`

**Immutability enforcement**:
```sql
-- The app_writer role used by the API has INSERT-only on this table
REVOKE UPDATE, DELETE ON log_entries FROM app_writer;
```

**Retention**: Rows with `timestamp < now() - interval '90 days'` are archived, not deleted (SC-04, spec constraint).

**Indexes**:
- `idx_logs_run_id` on `(run_id, timestamp ASC)` — primary access pattern
- `idx_logs_task_id` on `(task_id, timestamp ASC)`
- `idx_logs_status` on `(status, timestamp DESC)`
- `idx_logs_run_status` on `(run_id, status)`

---

### `reasoning_traces`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, NOT NULL | Generated |
| run_id | UUID | FK → execution_runs.id, NOT NULL | |
| task_id | UUID | FK → tasks.id, NOT NULL | |
| step_index | INT | NOT NULL | Order within a task |
| current_state | JSONB | NOT NULL | Agent's world model at this step |
| decision | TEXT | NOT NULL | What the agent decided to do |
| rationale | TEXT | NOT NULL | Why (chain-of-thought output) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Indexes**:
- `idx_traces_run_task` on `(run_id, task_id, step_index ASC)`

---

## State Transition Rules

### Goal Status Flow
```
received → planning → plan_ready → approved → executing → completed
                                └→ cancelled
                                                        └→ failed
```

### Task Status Flow
```
queued → running → succeeded
               └→ failed (retry if retriable, ≤3 attempts)
               └→ skipped (non-critical failures)
               └→ cancelled (operator cancels run)
```

### Run Status Flow
```
pending → running → completed
                └→ failed (critical-path task failed)
                └→ cancelled (operator cancelled)
```

---

## Validation Rules

| Rule | Enforcement |
|------|-------------|
| Goal text ≤ 2,000 characters | DB CHECK + API validation |
| Plan has 1–20 tasks | DB CHECK on `plans.task_count` |
| No circular task dependencies | Application-layer DAG validation before INSERT |
| Only one active run per plan | Partial unique index on `execution_runs` |
| Log entries immutable | DB role permissions (no UPDATE/DELETE on `log_entries`) |
| Destructive tasks require confirmation gate | Application-layer guard regardless of `auto_execute` |
