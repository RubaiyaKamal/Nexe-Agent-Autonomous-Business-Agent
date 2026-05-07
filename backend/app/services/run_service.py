import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution_run import ExecutionRun, RunStatus
from app.models.log_entry import LogEntry, LogStatus
from app.schemas.run import ExecutionRunResponse


async def create_run(
    plan_id: uuid.UUID,
    user_id: uuid.UUID,
    auto_execute: bool,
    db: AsyncSession,
) -> ExecutionRunResponse:
    run = ExecutionRun(
        plan_id=plan_id,
        triggered_by=user_id,
        status=RunStatus.pending,
        auto_execute=auto_execute,
    )
    db.add(run)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        from fastapi import HTTPException, status as http_status
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="An active run already exists for this plan",
        )

    # Enqueue execution
    from app.tasks.execute_run import execute_run_task
    execute_run_task.delay(str(run.id))

    await db.commit()
    await db.refresh(run)
    return ExecutionRunResponse.model_validate(run)


async def get_run(run_id: uuid.UUID, db: AsyncSession) -> ExecutionRunResponse | None:
    result = await db.execute(select(ExecutionRun).where(ExecutionRun.id == run_id))
    run = result.scalar_one_or_none()
    return ExecutionRunResponse.model_validate(run) if run else None


async def cancel_run(run_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> ExecutionRunResponse | None:
    result = await db.execute(select(ExecutionRun).where(ExecutionRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        return None

    run.status = RunStatus.cancelled

    log = LogEntry(
        run_id=run.id,
        task_id=None,
        status=LogStatus.run_cancelled,
        reasoning_summary=f"Run cancelled by user {user_id}",
        input_snapshot={},
        output_snapshot={},
    )
    db.add(log)
    await db.commit()
    await db.refresh(run)
    return ExecutionRunResponse.model_validate(run)
