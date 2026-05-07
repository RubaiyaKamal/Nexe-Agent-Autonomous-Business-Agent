import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.middleware.auth import require_current_user
from app.models.execution_run import ExecutionRun
from app.models.log_entry import LogEntry, LogStatus
from app.schemas.log import LogEntryResponse, PaginatedLogs
from app.schemas.run import ExecutionRunResponse
from app.services.run_service import cancel_run, get_run
from app.services.sse_service import subscribe_run

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.get("", response_model=list[ExecutionRunResponse])
async def list_runs(
    current_user: dict = Depends(require_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[ExecutionRunResponse]:
    result = await db.execute(
        select(ExecutionRun).where(ExecutionRun.triggered_by == current_user["user_id"])
    )
    runs = result.scalars().all()
    return [ExecutionRunResponse.model_validate(r) for r in runs]


@router.get("/{run_id}", response_model=ExecutionRunResponse)
async def get_run_detail(
    run_id: uuid.UUID,
    current_user: dict = Depends(require_current_user),
    db: AsyncSession = Depends(get_session),
) -> ExecutionRunResponse:
    run = await get_run(run_id, db)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.post("/{run_id}/cancel", response_model=ExecutionRunResponse)
async def cancel_run_endpoint(
    run_id: uuid.UUID,
    current_user: dict = Depends(require_current_user),
    db: AsyncSession = Depends(get_session),
) -> ExecutionRunResponse:
    run = await cancel_run(run_id, current_user["user_id"], db)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.get("/{run_id}/logs", response_model=PaginatedLogs)
async def get_run_logs(
    run_id: uuid.UUID,
    task_id: uuid.UUID | None = Query(None),
    log_status: LogStatus | None = Query(None, alias="status"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_current_user),
    db: AsyncSession = Depends(get_session),
) -> PaginatedLogs:
    query = select(LogEntry).where(LogEntry.run_id == run_id)
    if task_id:
        query = query.where(LogEntry.task_id == task_id)
    if log_status:
        query = query.where(LogEntry.status == log_status)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    rows_result = await db.execute(
        query.order_by(LogEntry.timestamp.asc()).limit(limit).offset(offset)
    )
    rows = rows_result.scalars().all()

    return PaginatedLogs(
        items=[LogEntryResponse.model_validate(r) for r in rows],
        total=total,
    )


@router.get("/{run_id}/status/stream")
async def run_status_stream(
    run_id: uuid.UUID,
    current_user: dict = Depends(require_current_user),
) -> StreamingResponse:
    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in subscribe_run(run_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
