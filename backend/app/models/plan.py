import uuid
from datetime import datetime
import enum

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PlanStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"
    cancelled = "cancelled"


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("task_count >= 1 AND task_count <= 20", name="ck_plan_task_count"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("goals.id"), unique=True, nullable=False)
    status: Mapped[PlanStatus] = mapped_column(
        Enum(PlanStatus, name="plan_status"), default=PlanStatus.draft, nullable=False
    )
    task_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
