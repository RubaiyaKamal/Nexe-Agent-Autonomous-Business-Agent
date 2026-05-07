import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log_entry import LogEntry, LogStatus


async def append_log_entry(
    run_id: uuid.UUID,
    task_id: uuid.UUID | None,
    status: LogStatus,
    reasoning_summary: str,
    input_snapshot: dict,
    output_snapshot: dict,
    db: AsyncSession,
    error_context: str | None = None,
    retry_count: int = 0,
) -> LogEntry:
    entry = LogEntry(
        run_id=run_id,
        task_id=task_id,
        status=status,
        reasoning_summary=reasoning_summary,
        input_snapshot=input_snapshot,
        output_snapshot=output_snapshot,
        error_context=error_context,
        retry_count=retry_count,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
