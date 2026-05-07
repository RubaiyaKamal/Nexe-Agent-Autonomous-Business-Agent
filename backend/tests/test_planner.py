import pytest

from app.agent.planner import LangGraphPlanner, PlannerError


@pytest.mark.asyncio
async def test_planner_returns_task_specs(mock_openai):
    planner = LangGraphPlanner()
    tasks = await planner.plan("Build a sales report")
    assert len(tasks) == 2
    assert tasks[0].type == "data_retrieval"
    assert tasks[1].type == "content_generation"
    assert tasks[1].dependencies  # has a dep on tasks[0]


@pytest.mark.asyncio
async def test_planner_raises_on_invalid_json(monkeypatch):
    class BadMessage:
        content = "not json at all"

    class BadChoice:
        message = BadMessage()

    class BadResponse:
        choices = [BadChoice()]

    class BadCompletions:
        async def create(self, **kwargs):
            return BadResponse()

    class BadChat:
        completions = BadCompletions()

    class BadClient:
        chat = BadChat()

    import app.agent.planner as planner_module
    monkeypatch.setattr(planner_module, "AsyncOpenAI", lambda **_: BadClient())

    planner = LangGraphPlanner()
    with pytest.raises(PlannerError):
        await planner.plan("anything")


@pytest.mark.asyncio
async def test_circular_dep_raises_planning_error(monkeypatch):
    import json

    class CircularMessage:
        content = json.dumps({"tasks": [
            {"description": "A", "dependencies": [1], "complexity": "low",
             "type": "data_retrieval", "is_critical_path": False, "timeout_seconds": 60},
            {"description": "B", "dependencies": [0], "complexity": "low",
             "type": "data_retrieval", "is_critical_path": False, "timeout_seconds": 60},
        ]})

    class CircChoice:
        message = CircularMessage()

    class CircResponse:
        choices = [CircChoice()]

    class CircCompletions:
        async def create(self, **kwargs):
            return CircResponse()

    class CircChat:
        completions = CircCompletions()

    class CircClient:
        chat = CircChat()

    import app.agent.planner as planner_module
    monkeypatch.setattr(planner_module, "AsyncOpenAI", lambda **_: CircClient())

    planner = LangGraphPlanner()
    with pytest.raises(PlannerError):
        await planner.plan("circular")
