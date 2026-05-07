import uuid
from datetime import datetime
import enum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    pending_clarification = "pending_clarification"


class ExecutionRun(Base):
    __tablename__ = "execution_runs"
    __table_args__ = (
        Index(
            "idx_runs_one_active_per_plan",
            "plan_id",
            unique=True,
            postgresql_where="status IN ('pending', 'running')",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    triggered_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"), default=RunStatus.pending, nullable=False
    )
    auto_execute: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tasks_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tasks_succeeded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tasks_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tasks_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
