from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from project root regardless of working directory
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"

# asyncpg only understands these query params; everything else gets dropped
_ASYNCPG_PARAMS = {"ssl", "application_name", "options", "server_settings"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str

    @field_validator("database_url")
    @classmethod
    def ensure_asyncpg(cls, v: str) -> str:
        """Normalize Neon/standard postgres:// URLs to postgresql+asyncpg://.

        Strips params asyncpg doesn't understand (sslmode, channel_binding, …)
        and converts sslmode=require → ssl=require.
        """
        if v.startswith("postgres://"):
            v = "postgresql+asyncpg://" + v[len("postgres://"):]
        elif v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://"):]

        parsed = urlparse(v)
        params: dict[str, str] = {k: vals[0] for k, vals in parse_qs(parsed.query).items()}

        # Translate sslmode → ssl
        sslmode = params.pop("sslmode", None)
        if sslmode and "ssl" not in params:
            if sslmode in ("require", "verify-full", "verify-ca"):
                params["ssl"] = "require"

        # Drop any remaining params asyncpg doesn't know
        params = {k: v for k, v in params.items() if k in _ASYNCPG_PARAMS}

        clean = parsed._replace(query=urlencode(params))
        return urlunparse(clean)

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Anthropic
    openai_api_key: str

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Tavily (data retrieval)
    tavily_api_key: str = ""

    # Agent
    task_timeout_seconds: int = 60
    log_retention_days: int = 90
    auto_execute_default: bool = False

    # Frontend / CORS
    frontend_url: str = "http://localhost:3000"

    # Observability
    otlp_endpoint: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
