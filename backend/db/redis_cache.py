"""
Semantic query cache using Redis.
Caches LLM responses keyed by a hash of the question + document filter.
"""
import json
import hashlib
import redis.asyncio as redis
from config import get_settings

settings = get_settings()
_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def _cache_key(question: str, doc_filter: str | None = None) -> str:
    raw = f"{question}|{doc_filter or 'all'}"
    return "rag:cache:" + hashlib.sha256(raw.encode()).hexdigest()


async def get_cached(question: str, doc_filter: str | None = None) -> dict | None:
    try:
        r = await get_redis()
        key = _cache_key(question, doc_filter)
        val = await r.get(key)
        if val:
            return json.loads(val)
    except Exception as e:
        logger.warning("redis_get_failed", error=str(e))
    return None


async def set_cache(
    question: str,
    response: dict,
    doc_filter: str | None = None,
    ttl: int | None = None,
) -> None:
    try:
        r = await get_redis()
        key = _cache_key(question, doc_filter)
        await r.setex(key, ttl or settings.redis_cache_ttl, json.dumps(response))
    except Exception as e:
        logger.warning("redis_set_failed", error=str(e))


async def invalidate_cache(doc_id: str | None = None) -> int:
    """Delete all cache keys (or optionally filtered by doc). Returns count deleted."""
    r = await get_redis()
    pattern = "rag:cache:*"
    keys = await r.keys(pattern)
    if keys:
        return await r.delete(*keys)
    return 0
