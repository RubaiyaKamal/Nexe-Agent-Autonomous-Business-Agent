import asyncio
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.services.auth_service import create_access_token, hash_password

TEST_DB_URL = "postgresql+asyncpg://nexe:nexe_dev@localhost:5432/nexe_agent_test"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def test_user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def test_token(test_user_id) -> str:
    return create_access_token(str(test_user_id), "test@example.com")


@pytest.fixture
def mock_openai(monkeypatch):
    """Return deterministic task list from planner."""
    import json

    class FakeMessage:
        content = json.dumps({"tasks": [
            {"description": "Retrieve data", "dependencies": [], "complexity": "low",
             "type": "data_retrieval", "is_critical_path": True, "timeout_seconds": 60},
            {"description": "Generate report", "dependencies": [0], "complexity": "medium",
             "type": "content_generation", "is_critical_path": False, "timeout_seconds": 60},
        ]})

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        async def create(self, **kwargs):
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    import app.agent.planner as planner_module
    monkeypatch.setattr(planner_module, "AsyncOpenAI", lambda **_: FakeClient())
    return FakeClient()
