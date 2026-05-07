import json
import logging
import uuid

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.agent.dag_validator import CircularDependencyError, validate_dag
from app.config import get_settings
from app.schemas.plan import TaskSpec

logger = logging.getLogger(__name__)
settings = get_settings()

_SYSTEM_PROMPT = """You are a business task planner. Given ANY input — including questions, research requests, or descriptive goals — decompose it into 1-10 concrete, actionable tasks that an AI agent can execute.

Return ONLY a valid JSON object in this exact format (no markdown, no extra text):
{
  "tasks": [
    {
      "description": "string — what this task does",
      "dependencies": [],
      "complexity": "low|medium|high",
      "type": "data_retrieval|content_generation|notification_dispatch",
      "is_critical_path": true|false,
      "timeout_seconds": 60
    }
  ]
}

Rules:
- "type" MUST be exactly one of: data_retrieval, content_generation, notification_dispatch — no other values are allowed
  - data_retrieval: research, gather information, fetch data, answer questions
  - content_generation: write, summarise, analyse, generate reports
  - notification_dispatch: send, deliver, notify
- dependencies is a list of zero-based integer indices referencing earlier tasks (e.g. [0, 1] means this task depends on tasks 0 and 1)
- No circular dependencies
- You MUST return at least 1 task — never return an empty tasks array
- At most 20 tasks
- Every task must have a clear, specific description"""


class PlannerError(Exception):
    pass


class LangGraphPlanner:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def plan(self, goal_text: str) -> list[TaskSpec]:
        logger.info("Planner: calling GPT-4o for goal: %s", goal_text[:120])

        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o",
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": f"Business goal: {goal_text}"},
                ],
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
        except Exception as exc:
            raise PlannerError(f"LLM call failed: {exc}") from exc

        logger.info("Planner raw response: %s", raw[:500] if raw else "<empty>")

        try:
            data = json.loads(raw)
            raw_tasks = data["tasks"]
        except (json.JSONDecodeError, KeyError) as exc:
            raise PlannerError(f"LLM output unparseable: {exc}\nRaw: {raw[:500]}") from exc

        if not raw_tasks:
            raise PlannerError("LLM returned 0 tasks — cannot create an empty plan")

        # Convert integer-indexed dependencies to temporary UUIDs
        temp_ids = [uuid.uuid4() for _ in raw_tasks]
        task_specs: list[TaskSpec] = []
        for i, raw_task in enumerate(raw_tasks):
            dep_indices: list[int] = raw_task.get("dependencies", [])
            dep_uuids = [
                temp_ids[idx]
                for idx in dep_indices
                if 0 <= idx < len(temp_ids) and idx != i
            ]
            raw_task["dependencies"] = dep_uuids
            try:
                task_specs.append(TaskSpec(**raw_task))
            except ValidationError as exc:
                raise PlannerError(f"Task {i} schema invalid: {exc}") from exc

        try:
            validate_dag(task_specs)
        except CircularDependencyError as exc:
            raise PlannerError(str(exc)) from exc

        logger.info("Planner: produced %d tasks", len(task_specs))
        return task_specs
