import logging
import os

from app.models.task import Task
from app.agent.handlers.data_retrieval import HandlerError

logger = logging.getLogger(__name__)


class NotificationDispatchHandler:
    def execute(self, task: Task, context: dict) -> dict:
        logger.info("NotificationDispatchHandler invoked for task %s", task.id)
        recipients = context.get("recipients", ["operator@example.com"])

        smtp_host = os.getenv("SMTP_HOST", "")
        if smtp_host:
            self._send_smtp(task, recipients, smtp_host)
        else:
            # Dev mode: log to stdout
            logger.info(
                "[DEV] Notification dispatch — task: %s | recipients: %s | context: %s",
                task.description,
                recipients,
                context,
            )

        return {"dispatched": True, "recipients": recipients}

    def _send_smtp(self, task: Task, recipients: list[str], smtp_host: str) -> None:
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["Subject"] = f"[Nexe Agent] Task complete: {task.description[:60]}"
        msg["From"] = os.getenv("SMTP_FROM", "noreply@nexe-agent.local")
        msg["To"] = ", ".join(recipients)
        msg.set_content(f"Task completed: {task.description}")

        try:
            with smtplib.SMTP(smtp_host, int(os.getenv("SMTP_PORT", "25"))) as s:
                s.send_message(msg)
        except Exception as exc:
            raise HandlerError(f"SMTP dispatch failed: {exc}") from exc
