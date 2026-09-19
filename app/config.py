from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _flag(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Settings:
    llm_provider: str = _flag("LLM_PROVIDER", "stub") or "stub"
    gemini_api_key: str = _flag("GEMINI_API_KEY")
    gemini_model: str = _flag("GEMINI_MODEL", "gemini-2.0-flash") or "gemini-2.0-flash"
    qdrant_url: str = _flag("QDRANT_URL")
    redis_url: str = _flag("REDIS_URL")
    database_url: str = _flag("DATABASE_URL", "sqlite:///./ops_sentry.db") or "sqlite:///./ops_sentry.db"
    collection: str = "helio_sops"
    embed_dim: int = 384
    retrieve_k: int = 5
    max_agent_steps: int = 4
    cache_ttl_seconds: int = 300
    ops_api_token: str = _flag("OPS_API_TOKEN")
    ops_env: str = _flag("OPS_ENV", "demo") or "demo"


settings = Settings()
