import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.middleware.auth import require_current_user
from app.models.goal import GoalStatus
from app.models.plan import PlanStatus
from app.schemas.goal import GoalCreate, GoalResponse
from app.schemas.plan import PlanResponse
from app.schemas.run import ExecutionRunResponse
from app.services.goal_service import create_goal, get_goal, update_goal_status
from app.services.plan_service import get_plan

router = APIRouter(prefix="/api/v1/goals", tags=["goals"])


@router.post("", response_model=GoalResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_goal(
    body: GoalCreate,
    current_user: dict = Depends(require_current_user),
    db: AsyncSession = Depends(get_session),
) -> GoalResponse:
    goal = await create_goal(body.text, current_user["user_id"], db)

    # Trigger async planning
    from app.tasks.plan_goal import plan_goal_task
    plan_goal_task.delay(str(goal.id))

    return goal


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal_detail(
    goal_id: uuid.UUID,
    current_user: dict = Depends(require_current_user),
    db: AsyncSession = Depends(get_session),
) -> GoalResponse:
    goal = await get_goal(goal_id, current_user["user_id"], db)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


@router.get("/{goal_id}/plan", response_model=PlanResponse)
async def get_goal_plan(
    goal_id: uuid.UUID,
    current_user: dict = Depends(require_current_user),
    db: AsyncSession = Depends(get_session),
) -> PlanResponse:
    goal = await get_goal(goal_id, current_user["user_id"], db)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    if goal.status in (GoalStatus.received, GoalStatus.planning):
        raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail="Planning in progress")

    plan = await get_plan(goal_id, db)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No plan found for this goal")
    return plan


@router.post("/{goal_id}/plan/approve", response_model=ExecutionRunResponse, status_code=status.HTTP_201_CREATED)
async def approve_plan(
    goal_id: uuid.UUID,
    current_user: dict = Depends(require_current_user),
    db: AsyncSession = Depends(get_session),
) -> ExecutionRunResponse:
    from sqlalchemy import select
    from app.models.plan import Plan
    from app.services.run_service import create_run

    plan = await get_plan(goal_id, db)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if plan.status != PlanStatus.draft:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Plan is already {plan.status}")

    # Check auto_execute: load user from DB
    from app.models.user import User
    result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    user = result.scalar_one_or_none()
    auto_exec = user.auto_execute if user else False

    # Destructive task guard: auto_execute never bypasses explicit confirmation
    # (All tasks go through this endpoint; auto_execute only affects UI polling)
    run = await create_run(plan.id, current_user["user_id"], auto_exec, db)
    return run


@router.post("/{goal_id}/plan/cancel", response_model=PlanResponse)
async def cancel_plan(
    goal_id: uuid.UUID,
    current_user: dict = Depends(require_current_user),
    db: AsyncSession = Depends(get_session),
) -> PlanResponse:
    from sqlalchemy import select
    from app.models.plan import Plan

    result = await db.execute(select(Plan).where(Plan.goal_id == goal_id))
    plan_row = result.scalar_one_or_none()
    if not plan_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if plan_row.status != PlanStatus.draft:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Plan is already {plan_row.status}")

    plan_row.status = PlanStatus.cancelled
    await update_goal_status(goal_id, GoalStatus.cancelled, db)
    await db.commit()

    return await get_plan(goal_id, db)
