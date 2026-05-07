import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reasoning_trace import ReasoningTrace


async def write_reasoning_trace(
    run_id: uuid.UUID,
    task_id: uuid.UUID,
    step_index: int,
    current_state: dict,
    decision: str,
    rationale: str,
    db: AsyncSession,
) -> ReasoningTrace:
    trace = ReasoningTrace(
        run_id=run_id,
        task_id=task_id,
        step_index=step_index,
        current_state=current_state,
        decision=decision,
        rationale=rationale,
    )
    db.add(trace)
    await db.commit()
    await db.refresh(trace)
    return trace
