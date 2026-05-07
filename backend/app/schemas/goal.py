import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.goal import GoalStatus


class GoalCreate(BaseModel):
    text: str = Field(..., max_length=2000, min_length=1)


class GoalResponse(BaseModel):
    id: uuid.UUID
    text: str
    submitted_by: uuid.UUID
    submitted_at: datetime
    status: GoalStatus

    model_config = {"from_attributes": True}
