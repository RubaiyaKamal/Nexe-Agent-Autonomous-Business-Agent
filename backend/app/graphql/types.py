import uuid
from datetime import datetime
from typing import Optional

import strawberry


@strawberry.type
class LogEntryType:
    id: uuid.UUID
    run_id: uuid.UUID
    task_id: Optional[uuid.UUID]
    timestamp: datetime
    status: str
    reasoning_summary: str
    input_snapshot: strawberry.scalars.JSON
    output_snapshot: strawberry.scalars.JSON
    error_context: Optional[str]
    retry_count: int


@strawberry.type
class ReasoningTraceType:
    id: uuid.UUID
    run_id: uuid.UUID
    task_id: uuid.UUID
    step_index: int
    current_state: strawberry.scalars.JSON
    decision: str
    rationale: str
    created_at: datetime


@strawberry.type
class StatusCountType:
    status: str
    count: int


@strawberry.type
class RunAuditSummaryType:
    run_id: uuid.UUID
    total_log_entries: int
    by_status: list[StatusCountType]


@strawberry.input
class LogFilterInput:
    run_id: Optional[uuid.UUID] = None
    task_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    limit: int = 100
    offset: int = 0
