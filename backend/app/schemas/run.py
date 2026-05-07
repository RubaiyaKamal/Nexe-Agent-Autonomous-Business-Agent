import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.execution_run import RunStatus


class ExecutionRunResponse(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    triggered_by: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
    status: RunStatus
    auto_execute: bool
    tasks_total: int
    tasks_succeeded: int
    tasks_failed: int
    tasks_skipped: int

    model_config = {"from_attributes": True}
