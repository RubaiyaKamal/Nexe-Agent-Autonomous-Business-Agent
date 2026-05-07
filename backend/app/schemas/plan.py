import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.plan import PlanStatus
from app.models.task import TaskStatus


class TaskSpec(BaseModel):
    description: str
    dependencies: list[uuid.UUID] = Field(default_factory=list)
    complexity: Literal["low", "medium", "high"]
    type: Literal["data_retrieval", "content_generation", "notification_dispatch"]
    is_critical_path: bool = False
    timeout_seconds: int = 60


class TaskResponse(BaseModel):
    id: uuid.UUID
    description: str
    task_type: str
    complexity: str
    status: TaskStatus
    dependencies: list[uuid.UUID]
    is_critical_path: bool
    order_index: int
    timeout_seconds: int

    model_config = {"from_attributes": True}


class PlanResponse(BaseModel):
    id: uuid.UUID
    goal_id: uuid.UUID
    status: PlanStatus
    task_count: int
    tasks: list[TaskResponse]
    created_at: datetime

    model_config = {"from_attributes": True}
