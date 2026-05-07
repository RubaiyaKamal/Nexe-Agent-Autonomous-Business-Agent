import uuid
from datetime import datetime
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LogStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    skipped = "skipped"
    retrying = "retrying"
    cancelled = "cancelled"
    notification = "notification"
    run_started = "run_started"
    run_completed = "run_completed"
    run_failed = "run_failed"
    run_cancelled = "run_cancelled"


class LogEntry(Base):
    __tablename__ = "log_entries"
    __table_args__ = (
        Index("idx_log_run_timestamp", "run_id", "timestamp"),
        Index("idx_log_run_task", "run_id", "task_id"),
        Index("idx_log_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("execution_runs.id"), nullable=False)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[LogStatus] = mapped_column(Enum(LogStatus, name="log_status"), nullable=False)
    reasoning_summary: Mapped[str] = mapped_column(Text, nullable=False)
    input_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    output_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    error_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
