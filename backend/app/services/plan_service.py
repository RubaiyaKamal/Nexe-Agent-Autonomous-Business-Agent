import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.goal import GoalStatus
from app.models.plan import Plan, PlanStatus
from app.models.task import Task, TaskType, ComplexityLevel
from app.schemas.plan import PlanResponse, TaskSpec
from app.services.goal_service import update_goal_status


async def create_plan(goal_id: uuid.UUID, tasks: list[TaskSpec], db: AsyncSession) -> PlanResponse:
    plan = Plan(goal_id=goal_id, status=PlanStatus.draft, task_count=len(tasks))
    db.add(plan)
    await db.flush()  # get plan.id before inserting tasks

    task_rows: list[Task] = []
    for i, spec in enumerate(tasks):
        task_rows.append(Task(
            plan_id=plan.id,
            description=spec.description,
            task_type=TaskType(spec.type),
            complexity=ComplexityLevel(spec.complexity),
            dependencies=spec.dependencies,
            is_critical_path=spec.is_critical_path,
            order_index=i,
            timeout_seconds=spec.timeout_seconds,
        ))
    db.add_all(task_rows)

    await update_goal_status(goal_id, GoalStatus.plan_ready, db)
    await db.commit()
    await db.refresh(plan)

    return await get_plan(goal_id, db)


async def get_plan(goal_id: uuid.UUID, db: AsyncSession) -> PlanResponse | None:
    result = await db.execute(select(Plan).where(Plan.goal_id == goal_id))
    plan = result.scalar_one_or_none()
    if not plan:
        return None

    task_result = await db.execute(
        select(Task).where(Task.plan_id == plan.id).order_by(Task.order_index)
    )
    task_rows = task_result.scalars().all()

    from app.schemas.plan import TaskResponse
    return PlanResponse(
        id=plan.id,
        goal_id=plan.goal_id,
        status=plan.status,
        task_count=plan.task_count,
        tasks=[TaskResponse.model_validate(t) for t in task_rows],
        created_at=plan.created_at,
    )
