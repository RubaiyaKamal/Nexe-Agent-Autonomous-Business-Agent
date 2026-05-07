import uuid
from collections import Counter
from typing import Optional

from sqlalchemy import func, select
from strawberry.types import Info

from app.graphql.types import LogEntryType, LogFilterInput, ReasoningTraceType, RunAuditSummaryType, StatusCountType
from app.models.log_entry import LogEntry
from app.models.reasoning_trace import ReasoningTrace


async def resolve_logs(filter: LogFilterInput, info: Info) -> list[LogEntryType]:
    db = info.context["db"]
    query = select(LogEntry)
    if filter.run_id:
        query = query.where(LogEntry.run_id == filter.run_id)
    if filter.task_id:
        query = query.where(LogEntry.task_id == filter.task_id)
    if filter.status:
        query = query.where(LogEntry.status == filter.status)
    query = query.order_by(LogEntry.timestamp.asc()).limit(filter.limit).offset(filter.offset)

    result = await db.execute(query)
    rows = result.scalars().all()
    return [_map_log(r) for r in rows]


async def resolve_log_entry(id: uuid.UUID, info: Info) -> Optional[LogEntryType]:
    db = info.context["db"]
    result = await db.execute(select(LogEntry).where(LogEntry.id == id))
    row = result.scalar_one_or_none()
    return _map_log(row) if row else None


async def resolve_reasoning_traces(run_id: uuid.UUID, task_id: Optional[uuid.UUID], info: Info) -> list[ReasoningTraceType]:
    db = info.context["db"]
    query = select(ReasoningTrace).where(ReasoningTrace.run_id == run_id)
    if task_id:
        query = query.where(ReasoningTrace.task_id == task_id)
    query = query.order_by(ReasoningTrace.step_index.asc())
    result = await db.execute(query)
    return [_map_trace(r) for r in result.scalars().all()]


async def resolve_run_audit_summary(run_id: uuid.UUID, info: Info) -> RunAuditSummaryType:
    db = info.context["db"]
    result = await db.execute(
        select(LogEntry.status, func.count().label("cnt"))
        .where(LogEntry.run_id == run_id)
        .group_by(LogEntry.status)
    )
    rows = result.all()
    total = sum(r.cnt for r in rows)
    by_status = [StatusCountType(status=r.status, count=r.cnt) for r in rows]
    return RunAuditSummaryType(run_id=run_id, total_log_entries=total, by_status=by_status)


def _map_log(r: LogEntry) -> LogEntryType:
    return LogEntryType(
        id=r.id, run_id=r.run_id, task_id=r.task_id, timestamp=r.timestamp,
        status=r.status.value, reasoning_summary=r.reasoning_summary,
        input_snapshot=r.input_snapshot, output_snapshot=r.output_snapshot,
        error_context=r.error_context, retry_count=r.retry_count,
    )


def _map_trace(r: ReasoningTrace) -> ReasoningTraceType:
    return ReasoningTraceType(
        id=r.id, run_id=r.run_id, task_id=r.task_id, step_index=r.step_index,
        current_state=r.current_state, decision=r.decision, rationale=r.rationale,
        created_at=r.created_at,
    )
