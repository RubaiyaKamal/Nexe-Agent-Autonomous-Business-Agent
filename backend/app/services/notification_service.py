import logging
import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log_entry import LogStatus
from app.services.log_service import append_log_entry

logger = logging.getLogger(__name__)


async def notify_operator(
    run_id: uuid.UUID,
    user_id: uuid.UUID,
    message: str,
    db: AsyncSession,
) -> None:
    await append_log_entry(
        run_id=run_id,
        task_id=None,
        status=LogStatus.notification,
        reasoning_summary=message,
        input_snapshot={"user_id": str(user_id)},
        output_snapshot={},
        db=db,
    )

    smtp_host = os.getenv("SMTP_HOST", "")
    if smtp_host:
        _send_smtp(message, smtp_host)
    else:
        logger.warning("[DEV] Operator notification: %s | run_id=%s", message, run_id)


def _send_smtp(message: str, smtp_host: str) -> None:
    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = "[Nexe Agent] Critical failure notification"
    msg["From"] = os.getenv("SMTP_FROM", "noreply@nexe-agent.local")
    msg["To"] = os.getenv("OPERATOR_EMAIL", "operator@example.com")
    msg.set_content(message)

    try:
        with smtplib.SMTP(smtp_host, int(os.getenv("SMTP_PORT", "25"))) as s:
            s.send_message(msg)
    except Exception as exc:
        logger.error("SMTP notification failed: %s", exc)
