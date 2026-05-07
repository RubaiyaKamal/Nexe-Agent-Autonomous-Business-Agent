import asyncio
import uuid

from app.agent.planner import LangGraphPlanner, PlannerError
from app.database import celery_session
from app.models.goal import GoalStatus
from app.services.goal_service import update_goal_status
from app.services.plan_service import create_plan
from app.worker import celery_app


@celery_app.task(name="app.tasks.plan_goal.plan_goal_task", bind=True)
def plan_goal_task(self, goal_id: str) -> None:
    asyncio.run(_async_plan_goal(goal_id))


async def _async_plan_goal(goal_id_str: str) -> None:
    goal_id = uuid.UUID(goal_id_str)
    goal_text = await _get_goal_text(goal_id_str)
    async with celery_session() as db:
        await update_goal_status(goal_id, GoalStatus.planning, db)
        try:
            planner = LangGraphPlanner()
            tasks = await planner.plan(goal_text)
            await create_plan(goal_id, tasks, db)
        except (PlannerError, Exception) as exc:
            await update_goal_status(goal_id, GoalStatus.failed, db)
            raise


async def _get_goal_text(goal_id: str) -> str:
    from sqlalchemy import select
    from app.models.goal import Goal
    async with celery_session() as db:
        result = await db.execute(select(Goal).where(Goal.id == uuid.UUID(goal_id)))
        goal = result.scalar_one_or_none()
        return goal.text if goal else ""
