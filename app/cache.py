from __future__ import annotations

import hashlib
import json

from app.config import settings
from app.schemas import AskResponse

_memory: dict[str, str] = {}
_redis = None


def _key(query: str) -> str:
    return "ops:" + hashlib.sha256(query.strip().lower().encode()).hexdigest()


def _redis_client():
    global _redis
    if _redis is False:
        return None
    if _redis is not None:
        return _redis
    if not settings.redis_url:
        _redis = False
        return None
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        _redis = client
        return client
    except Exception:
        _redis = False
        return None


def get_cached(query: str) -> AskResponse | None:
    key = _key(query)
    raw = None
    client = _redis_client()
    if client is not None:
        raw = client.get(key)
    else:
        raw = _memory.get(key)
    if not raw:
        return None
    data = json.loads(raw)
    response = AskResponse.model_validate(data)
    response.cached = True
    return response


def put_cached(query: str, response: AskResponse) -> None:
    if response.blocked or response.needs_confirmation:
        return
    key = _key(query)
    payload = response.model_dump_json()
    client = _redis_client()
    if client is not None:
        client.setex(key, settings.cache_ttl_seconds, payload)
    else:
        _memory[key] = payload
