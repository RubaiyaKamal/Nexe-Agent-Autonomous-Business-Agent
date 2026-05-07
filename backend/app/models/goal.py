import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.database import Base


class GoalStatus(str, enum.Enum):
    received = "received"
    planning = "planning"
    plan_ready = "plan_ready"
    approved = "approved"
    executing = "executing"
    completed = "completed"
    cancelled = "cancelled"
    failed = "failed"


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint("char_length(text) <= 2000", name="ck_goal_text_length"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus, name="goal_status"), default=GoalStatus.received, nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
