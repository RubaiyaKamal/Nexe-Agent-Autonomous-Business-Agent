import json
import uuid
from typing import Any

from openai import AsyncOpenAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, ValidationError

from app.agent.dag_validator import CircularDependencyError, validate_dag
from app.config import get_settings
from app.schemas.plan import TaskSpec

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


class _PlannerState(BaseModel):
    goal_text: str
    raw_output: str = ""
    tasks: list[TaskSpec] = []
    error: str = ""


class LangGraphPlanner:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def plan(self, goal_text: str) -> list[TaskSpec]:
        graph = self._build_graph()
        result = await graph.ainvoke(_PlannerState(goal_text=goal_text))
        if result["error"]:
            raise PlannerError(result["error"])
        return result["tasks"]

    def _build_graph(self) -> Any:
        builder = StateGraph(_PlannerState)
        builder.add_node("plan", self._planning_node)
        builder.set_entry_point("plan")
        builder.add_edge("plan", END)
        return builder.compile()

    async def _planning_node(self, state: _PlannerState) -> dict:
        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o",
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": f"Business goal: {state.goal_text}"},
                ],
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
        except Exception as exc:
            return {"error": f"LLM call failed: {exc}"}

        try:
            data = json.loads(raw)
            raw_tasks = data["tasks"]
        except (json.JSONDecodeError, KeyError) as exc:
            return {"error": f"LLM output unparseable: {exc}\nRaw: {raw[:500]}"}

        # Convert integer-indexed dependencies to temporary UUIDs
        temp_ids = [uuid.uuid4() for _ in raw_tasks]
        task_specs: list[TaskSpec] = []
        for i, raw_task in enumerate(raw_tasks):
            dep_indices: list[int] = raw_task.get("dependencies", [])
            dep_uuids = []
            for idx in dep_indices:
                if 0 <= idx < len(temp_ids) and idx != i:
                    dep_uuids.append(temp_ids[idx])
            raw_task["dependencies"] = dep_uuids
            try:
                task_specs.append(TaskSpec(**raw_task))
            except ValidationError as exc:
                return {"error": f"Task {i} schema invalid: {exc}"}

        if not task_specs:
            return {"error": "LLM returned 0 tasks — cannot create an empty plan"}

        try:
            validate_dag(task_specs)
        except CircularDependencyError as exc:
            return {"error": str(exc)}

        return {"raw_output": raw, "tasks": task_specs}
