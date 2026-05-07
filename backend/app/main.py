from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine
from app.graphql.schema import graphql_router
from app.routers import auth, goals, runs, users


@asynccontextmanager
async def lifespan(application: FastAPI):
    async with engine.begin():
        pass
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title="Nexe Agent",
        description="Autonomous Business Agent API",
        version="0.1.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # OpenTelemetry (no-op if OTLP_ENDPOINT is empty)
    if settings.otlp_endpoint:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            FastAPIInstrumentor.instrument_app(application)
        except ImportError:
            pass

    application.include_router(auth.router)
    application.include_router(goals.router)
    application.include_router(runs.router)
    application.include_router(users.router)
    application.include_router(graphql_router, prefix="/graphql")

    return application


app = create_app()


@app.get("/api/v1/health", tags=["health"])
async def health():
    from sqlalchemy import text
    import redis.asyncio as aioredis

    settings = get_settings()

    # DB probe
    db_status = "ok"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # Redis probe
    redis_status = "ok"
    try:
        r = aioredis.from_url(settings.redis_url, ssl_cert_reqs=None)
        await r.ping()
        await r.aclose()
    except Exception:
        redis_status = "error"

    return {"status": "ok", "db": db_status, "redis": redis_status}
