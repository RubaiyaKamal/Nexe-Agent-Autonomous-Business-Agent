"""Daily log archive task: moves entries older than LOG_RETENTION_DAYS to archive table."""
import asyncio
from datetime import datetime, timedelta, timezone

from app.worker import celery_app


@celery_app.task(name="app.tasks.archive_logs.archive_old_logs")
def archive_old_logs() -> None:
    asyncio.run(_async_archive())


async def _async_archive() -> None:
    from sqlalchemy import text

    from app.config import get_settings
    from app.database import AsyncSessionLocal

    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.log_retention_days)

    async with AsyncSessionLocal() as db:
        # Ensure archive table exists (same schema, no FK constraints)
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS archived_log_entries
            AS SELECT * FROM log_entries WHERE false;
        """))

        # Move old entries
        await db.execute(text("""
            WITH moved AS (
                DELETE FROM log_entries
                WHERE timestamp < :cutoff
                RETURNING *
            )
            INSERT INTO archived_log_entries SELECT * FROM moved;
        """), {"cutoff": cutoff})

        await db.commit()
