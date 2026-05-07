# Phase 0 Research: Autonomous Business Agent

**Feature**: 1-autonomous-business-agent  
**Date**: 2026-05-04  
**Status**: Complete — all unknowns resolved

---

## Decision 1: Multi-Step AI Agent Reasoning Pattern

**Decision**: LangGraph + ReAct (Reasoning + Acting) prompting pattern

**Rationale**: LangGraph provides a graph-based state machine for agent orchestration — nodes are work units, edges are control flow. ReAct combines chain-of-thought reasoning with tool invocation in each step, which directly maps to "evaluate output → decide next step → act". This combination eliminates the need for manual state threading and provides built-in conditional branching (spec FR-03).

**Alternatives considered**:
- Chain-of-Thought alone: Reasoning only, no action capability — insufficient.
- Raw tool-calling loops: Possible but requires manual state management across turns.
- Auto-GPT-style agents: Less deterministic; harder to guarantee dependency ordering (FR-04).

---

## Decision 2: Immutable Audit Log Storage

**Decision**: PostgreSQL append-only table with database-level write protection (INSERT-only role, no UPDATE/DELETE grants on log table)

**Rationale**: Append-only relational tables satisfy immutability (FR-05), retain full ACID guarantees, and are natively queryable by run_id, task_id, status, and date range. Event sourcing on top of Postgres gives state reconstruction without a separate event store. No entry can be altered once written because the application role literally has no UPDATE or DELETE permission on the log table.

**Alternatives considered**:
- EventStoreDB: Dedicated event store, more sophisticated — unnecessary complexity for this log volume.
- S3 write-once storage: Good for archival; poor for sub-10s search queries (SC-05).
- Traditional audit columns (updated_at, deleted_at): Requires dual-write and doesn't guarantee immutability.

---

## Decision 3: Async Task Execution

**Decision**: Celery + Redis (broker + result backend)

**Rationale**: Celery provides distributed task execution with built-in retry logic, exponential back-off, and per-task timeouts — directly satisfying FR-04 (configurable timeout) and FR-06 (retriable failures with 3-retry back-off). Redis doubles as broker and result store, reducing operational components. Celery integrates cleanly with FastAPI via asyncio bridges.

**Alternatives considered**:
- Pure asyncio workers: No distributed execution; single-process only.
- RabbitMQ: More durable message delivery but higher ops overhead; Redis sufficient for this use case.
- Managed queues (SQS, Cloud Tasks): Eliminates ops but increases latency; less suitable for sub-60s task timeouts.

---

## Decision 4: Real-Time Status Delivery

**Decision**: Server-Sent Events (SSE) via FastAPI streaming response

**Rationale**: Run status is a one-directional server-to-client stream (operator watches progress). SSE is simpler than WebSocket for this use case, has built-in browser reconnection, and is natively supported by FastAPI's `StreamingResponse`. No bidirectional communication is needed during execution — SSE is the correct fit.

**Alternatives considered**:
- WebSockets: Necessary only for bidirectional communication; over-engineered here.
- Long polling: Functional but creates unnecessary network churn; worse latency than SSE.
- Push notifications: Out-of-scope for MVP; appropriate for mobile notifications in a later phase.

---

## Decision 5: API Design

**Decision**: REST (goal submission, plan approval, run management) + GraphQL (audit log queries)

**Rationale**: Goal submission and plan approval are simple write operations — REST POST endpoints are the right abstraction. Audit log queries require flexible, nested filtering by run_id, task_id, status, and date range (FR-05) — GraphQL avoids creating many bespoke REST endpoints. This hybrid gives simplicity for writes and power for reads.

**Alternatives considered**:
- Pure REST: Requires many query-string-heavy endpoints for log filtering; awkward UX.
- Pure GraphQL: Over-engineered for simple goal submission; adds client query overhead.
- gRPC: Right for internal microservices; wrong for operator-facing dashboard API.

---

## Decision 6: Backend Framework

**Decision**: Python + FastAPI

**Rationale**: FastAPI is async-first, essential for an agent backend where every operation involves long I/O (LLM calls, Celery task awaiting, SSE streaming). Built-in OpenAPI generation satisfies the REST contract documentation requirement. Strong Python AI ecosystem (LangGraph, Anthropic SDK, Celery) integrates naturally.

**Alternatives considered**:
- Django: Mature ORM and admin — but blocking-by-default; poor fit for async agent I/O.
- Flask: Lightweight, widely used — but poor native async support and no auto-validation.
- Node.js/Express: Good async but weaker AI ecosystem for Python-native LangGraph.

---

## Resolved Tech Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Backend API | Python + FastAPI | Async-first, OpenAPI, AI ecosystem |
| Agent Reasoning | LangGraph + ReAct | Stateful graph, conditional branching |
| LLM | Anthropic Claude (via SDK) | Most capable available; best reasoning |
| Task Queue | Celery + Redis | Distributed, retry, timeout |
| Database | PostgreSQL | ACID, append-only logs, queryable |
| Real-time | SSE (FastAPI StreamingResponse) | Uni-directional, auto-reconnect |
| Write API | REST/JSON | Simple, standard |
| Query API | GraphQL (Strawberry) | Flexible audit log queries |
| Frontend | Next.js (React) | Operator dashboard |
| Auth | JWT (short-lived) + refresh tokens | Stateless, secure |

---

## All NEEDS CLARIFICATION Markers: Resolved

None were generated at spec stage. All technology choices resolved via research above.
