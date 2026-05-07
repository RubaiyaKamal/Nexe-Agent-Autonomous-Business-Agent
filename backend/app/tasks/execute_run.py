import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.agent.react_loop import ReActLoop
from app.database import celery_session
from app.models.execution_run import ExecutionRun, RunStatus
from app.models.log_entry import LogStatus
from app.models.task import Task, TaskStatus
from app.services.log_service import append_log_entry
from app.services.sse_service import publish_run_event
from app.worker import celery_app


@celery_app.task(name="app.tasks.execute_run.execute_run_task", bind=True)
def execute_run_task(self, run_id: str) -> None:
    asyncio.run(_async_execute_run(run_id))


async def _async_execute_run(run_id_str: str) -> None:
    run_id = uuid.UUID(run_id_str)

    # Load run + tasks, mark run as running
    async with celery_session() as db:
        result = await db.execute(select(ExecutionRun).where(ExecutionRun.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            return

        tasks = list(
            (
                await db.execute(
                    select(Task).where(Task.plan_id == run.plan_id).order_by(Task.order_index)
                )
            ).scalars().all()
        )

        run.status = RunStatus.running
        run.tasks_total = len(tasks)
        await db.commit()

    await publish_run_event(run_id, "run_started", {"run_id": str(run_id), "tasks_total": len(tasks)})

    async with celery_session() as db:
        await append_log_entry(
            run_id=run_id, task_id=None, status=LogStatus.run_started,
            reasoning_summary=f"Run started with {len(tasks)} tasks",
            input_snapshot={}, output_snapshot={}, db=db,
        )

    prior_outputs: dict = {}
    succeeded = failed = skipped = 0
    failed_ids: set[uuid.UUID] = set()
    abort = False
    react = ReActLoop()

    for task in tasks:
        dep_failed = any(d in failed_ids for d in task.dependencies)

        if abort or dep_failed:
            async with celery_session() as db:
                t = (await db.execute(select(Task).where(Task.id == task.id))).scalar_one()
                t.status = TaskStatus.skipped
                await append_log_entry(
                    run_id=run_id, task_id=task.id, status=LogStatus.skipped,
                    reasoning_summary="Skipped: dependency failed or run aborted",
                    input_snapshot={}, output_snapshot={}, db=db,
                )
            skipped += 1
            failed_ids.add(task.id)
            await publish_run_event(
                run_id, "task_skipped",
                {"task_id": str(task.id), "description": task.description},
            )
            continue

        # Mark running
        async with celery_session() as db:
            t = (await db.execute(select(Task).where(Task.id == task.id))).scalar_one()
            t.status = TaskStatus.running
            await db.commit()

        await publish_run_event(
            run_id, "task_started",
            {"task_id": str(task.id), "description": task.description},
        )

        # Execute with retries (critical-path tasks get only 1 attempt)
        max_retries = 1 if task.is_critical_path else 3
        task_result = None
        for attempt in range(max_retries):
            async with celery_session() as db:
                task_result = await react.execute_task(task, run_id, prior_outputs, db)
            if task_result.status != "failed" or task_result.failure_type == "non_retriable":
                break
            if attempt < max_retries - 1:
                async with celery_session() as db:
                    t = (await db.execute(select(Task).where(Task.id == task.id))).scalar_one()
                    t.status = TaskStatus.retrying
                    await append_log_entry(
                        run_id=run_id, task_id=task.id, status=LogStatus.retrying,
                        reasoning_summary=f"Retrying (attempt {attempt + 2}/{max_retries})",
                        input_snapshot={"attempt": attempt + 1}, output_snapshot={},
                        error_context=task_result.error_context, retry_count=attempt + 1, db=db,
                    )

        # Record final outcome
        async with celery_session() as db:
            t = (await db.execute(select(Task).where(Task.id == task.id))).scalar_one()
            if task_result.status == "succeeded":
                t.status = TaskStatus.succeeded
                succeeded += 1
                prior_outputs[str(task.id)] = task_result.output
                await append_log_entry(
                    run_id=run_id, task_id=task.id, status=LogStatus.succeeded,
                    reasoning_summary=task_result.reasoning_summary,
                    input_snapshot={"prior_outputs_keys": list(prior_outputs.keys())},
                    output_snapshot=task_result.output, db=db,
                )
                await publish_run_event(run_id, "task_completed", {
                    "task_id": str(task.id),
                    "description": task.description,
                    "output": task_result.output,
                })
            else:
                t.status = TaskStatus.failed
                failed += 1
                failed_ids.add(task.id)
                await append_log_entry(
                    run_id=run_id, task_id=task.id, status=LogStatus.failed,
                    reasoning_summary=task_result.reasoning_summary,
                    input_snapshot={}, output_snapshot={},
                    error_context=task_result.error_context, db=db,
                )
                await publish_run_event(run_id, "task_failed", {
                    "task_id": str(task.id),
                    "description": task.description,
                    "error": task_result.error_context,
                })
                if task.is_critical_path:
                    abort = True

    # Finalize run
    final_status = RunStatus.completed if failed == 0 else RunStatus.failed
    async with celery_session() as db:
        result = await db.execute(select(ExecutionRun).where(ExecutionRun.id == run_id))
        run = result.scalar_one()
        run.status = final_status
        run.tasks_succeeded = succeeded
        run.tasks_failed = failed
        run.tasks_skipped = skipped
        run.ended_at = datetime.now(timezone.utc)
        log_status = LogStatus.run_completed if final_status == RunStatus.completed else LogStatus.run_failed
        await append_log_entry(
            run_id=run_id, task_id=None, status=log_status,
            reasoning_summary=(
                f"Run {final_status.value}: "
                f"{succeeded} succeeded, {failed} failed, {skipped} skipped"
            ),
            input_snapshot={},
            output_snapshot={"succeeded": succeeded, "failed": failed, "skipped": skipped},
            db=db,
        )

    sse_event = "run_completed" if final_status == RunStatus.completed else "run_failed"
    await publish_run_event(run_id, sse_event, {
        "run_id": str(run_id),
        "status": final_status.value,
        "tasks_succeeded": succeeded,
        "tasks_failed": failed,
        "tasks_skipped": skipped,
    })
