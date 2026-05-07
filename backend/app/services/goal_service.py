import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal, GoalStatus
from app.schemas.goal import GoalResponse


async def create_goal(text: str, user_id: uuid.UUID, db: AsyncSession) -> GoalResponse:
    goal = Goal(text=text, submitted_by=user_id, status=GoalStatus.received)
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return GoalResponse.model_validate(goal)


async def get_goal(goal_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> GoalResponse | None:
    result = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.submitted_by == user_id)
    )
    goal = result.scalar_one_or_none()
    return GoalResponse.model_validate(goal) if goal else None


async def list_goals(user_id: uuid.UUID, db: AsyncSession) -> list[GoalResponse]:
    result = await db.execute(
        select(Goal).where(Goal.submitted_by == user_id).order_by(Goal.submitted_at.desc())
    )
    return [GoalResponse.model_validate(g) for g in result.scalars().all()]


async def update_goal_status(goal_id: uuid.UUID, new_status: GoalStatus, db: AsyncSession) -> None:
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    if goal:
        goal.status = new_status
        await db.commit()
