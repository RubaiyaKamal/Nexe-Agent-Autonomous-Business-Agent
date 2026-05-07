import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.log_entry import LogStatus


class LogEntryResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    task_id: uuid.UUID | None
    timestamp: datetime
    status: LogStatus
    reasoning_summary: str
    input_snapshot: dict
    output_snapshot: dict
    error_context: str | None
    retry_count: int

    model_config = {"from_attributes": True}


class PaginatedLogs(BaseModel):
    items: list[LogEntryResponse]
    total: int
