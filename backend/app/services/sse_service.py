import json
import ssl
import uuid
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()


def _get_redis() -> aioredis.Redis:
    kwargs: dict = {"decode_responses": True}
    if settings.redis_url.startswith("rediss://"):
        kwargs["ssl_cert_reqs"] = "none"
    return aioredis.from_url(settings.redis_url, **kwargs)


async def publish_run_event(run_id: uuid.UUID, event_type: str, payload: dict) -> None:
    r = _get_redis()
    message = json.dumps({"event": event_type, "payload": payload})
    await r.publish(f"run:{run_id}", message)
    await r.aclose()


async def subscribe_run(run_id: uuid.UUID) -> AsyncGenerator[dict, None]:
    r = _get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(f"run:{run_id}")

    _TERMINAL = {"run_completed", "run_failed", "run_cancelled"}

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = json.loads(message["data"])
            yield data
            if data.get("event") in _TERMINAL:
                break
    finally:
        await pubsub.unsubscribe(f"run:{run_id}")
        await r.aclose()
