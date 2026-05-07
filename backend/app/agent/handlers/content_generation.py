import logging
from pathlib import Path

from openai import OpenAI

from app.config import get_settings
from app.models.task import Task
from app.agent.handlers.data_retrieval import HandlerError

logger = logging.getLogger(__name__)
settings = get_settings()

# Resolve once: backend/artifacts/
_ARTIFACTS_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "artifacts"


class ContentGenerationHandler:
    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key)

    def execute(self, task: Task, context: dict) -> dict:
        logger.info("ContentGenerationHandler invoked for task %s", task.id)
        prior_summary = "\n".join(
            f"- {k}: {v}" for k, v in context.items()
        ) or "No prior context."

        try:
            response = self._client.chat.completions.create(
                model="gpt-4o",
                max_tokens=1024,
                timeout=task.timeout_seconds,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business content generator. Produce concise, professional output.",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Task: {task.description}\n\n"
                            f"Prior context:\n{prior_summary}\n\n"
                            "Generate the requested content."
                        ),
                    },
                ],
            )
            content = response.choices[0].message.content
            artifact_path = self._save_artifact(task.id, content)
            logger.info("Content artifact saved to %s", artifact_path)
            return {"content": content, "artifact_path": str(artifact_path)}
        except Exception as exc:
            raise HandlerError(f"content_generation failed: {exc}") from exc

    def _save_artifact(self, task_id: object, content: str) -> Path:
        out_dir = _ARTIFACTS_ROOT / str(task_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        artifact = out_dir / "content.md"
        artifact.write_text(content, encoding="utf-8")
        return artifact
