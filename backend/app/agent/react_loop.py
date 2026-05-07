import uuid
from typing import Any, Literal

from langgraph.graph import END, StateGraph
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import get_settings
from app.models.task import Task, TaskType
from app.services.log_service import append_log_entry
from app.services.trace_service import write_reasoning_trace

settings = get_settings()


class TaskResult(BaseModel):
    status: Literal["succeeded", "failed", "skipped"]
    output: dict
    reasoning_summary: str
    error_context: str | None = None
    failure_type: Literal["retriable", "non_retriable", "critical_path"] | None = None


class _LoopState(BaseModel):
    task_id: str
    task_description: str
    task_type: str
    timeout_seconds: int
    prior_outputs: dict
    step_index: int = 0
    decision: str = ""
    rationale: str = ""
    handler_output: dict = {}
    error: str = ""
    is_valid: bool = True


class ReActLoop:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def execute_task(
        self,
        task: Task,
        run_id: uuid.UUID,
        prior_outputs: dict,
        db: Any,
    ) -> TaskResult:
        graph = self._build_graph()
        initial = _LoopState(
            task_id=str(task.id),
            task_description=task.description,
            task_type=task.task_type.value,
            timeout_seconds=task.timeout_seconds,
            prior_outputs=prior_outputs,
        )
        result = await graph.ainvoke(initial)

        if result["error"]:
            return TaskResult(
                status="failed",
                output={},
                reasoning_summary=result["rationale"] or result["error"],
                error_context=result["error"],
                failure_type="retriable",
            )

        # Persist reasoning trace after think node completed
        from app.models.log_entry import LogStatus
        await write_reasoning_trace(
            run_id=run_id,
            task_id=task.id,
            step_index=result["step_index"],
            current_state={"prior_outputs": prior_outputs, "description": task.description},
            decision=result["decision"],
            rationale=result["rationale"],
            db=db,
        )

        if not result["is_valid"]:
            return TaskResult(
                status="failed",
                output=result["handler_output"],
                reasoning_summary=result["rationale"],
                error_context="Output validation failed",
                failure_type="non_retriable",
            )

        return TaskResult(
            status="succeeded",
            output=result["handler_output"],
            reasoning_summary=result["rationale"],
        )

    def _build_graph(self) -> Any:
        builder = StateGraph(_LoopState)
        builder.add_node("observe", self._observe_node)
        builder.add_node("think", self._think_node)
        builder.add_node("act", self._act_node)
        builder.add_node("evaluate", self._evaluate_node)
        builder.set_entry_point("observe")
        builder.add_edge("observe", "think")
        builder.add_edge("think", "act")
        builder.add_edge("act", "evaluate")
        builder.add_edge("evaluate", END)
        return builder.compile()

    async def _observe_node(self, state: _LoopState) -> dict:
        return {"step_index": state.step_index + 1}

    async def _think_node(self, state: _LoopState) -> dict:
        prior_summary = "\n".join(f"- {k}: {v}" for k, v in state.prior_outputs.items()) or "None"
        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o",
                max_tokens=512,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a business agent reasoning step. "
                            "Given a task, produce a decision and brief rationale. "
                            "Reply in JSON: {\"decision\": \"...\", \"rationale\": \"...\"}"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Task: {state.task_description}\n"
                            f"Type: {state.task_type}\n"
                            f"Prior outputs:\n{prior_summary}"
                        ),
                    },
                ],
                response_format={"type": "json_object"},
            )
            import json
            data = json.loads(response.choices[0].message.content)
            return {"decision": data.get("decision", ""), "rationale": data.get("rationale", "")}
        except Exception as exc:
            return {"error": f"think node failed: {exc}"}

    async def _act_node(self, state: _LoopState) -> dict:
        if state.error:
            return {}
        try:
            from app.agent.handlers.data_retrieval import DataRetrievalHandler
            from app.agent.handlers.content_generation import ContentGenerationHandler
            from app.agent.handlers.notification_dispatch import NotificationDispatchHandler
            from app.models.task import Task as TaskModel

            mock_task = type("T", (), {
                "id": uuid.UUID(state.task_id),
                "description": state.task_description,
                "timeout_seconds": state.timeout_seconds,
            })()

            handlers = {
                "data_retrieval": DataRetrievalHandler(),
                "content_generation": ContentGenerationHandler(),
                "notification_dispatch": NotificationDispatchHandler(),
            }
            handler = handlers.get(state.task_type)
            if not handler:
                return {"error": f"Unknown task type: {state.task_type}"}

            output = handler.execute(mock_task, state.prior_outputs)
            return {"handler_output": output}
        except Exception as exc:
            return {"error": str(exc)}

    async def _evaluate_node(self, state: _LoopState) -> dict:
        if state.error:
            return {"is_valid": False}
        # Basic validation: output must be a non-empty dict
        return {"is_valid": bool(state.handler_output)}
