"""Lightweight retrieval caching with optional Redis backing."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import asdict, is_dataclass
from typing import Any, Protocol


class RetrievalCache(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any) -> None: ...


class InMemoryRetrievalCache:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at < time.time():
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.time() + self.ttl_seconds, value)


class RedisRetrievalCache:
    def __init__(self, redis_client: Any, *, ttl_seconds: int = 3600, prefix: str = "course_search") -> None:
        self.redis_client = redis_client
        self.ttl_seconds = ttl_seconds
        self.prefix = prefix

    def _redis_key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> Any | None:
        payload = self.redis_client.get(self._redis_key(key))
        if payload is None:
            return None
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        return json.loads(payload)

    def set(self, key: str, value: Any) -> None:
        payload = json.dumps(value, ensure_ascii=False)
        self.redis_client.setex(self._redis_key(key), self.ttl_seconds, payload)


def create_retrieval_cache(ttl_seconds: int = 3600, prefix: str = "course_search") -> RetrievalCache:
    redis_url = os.getenv("REDIS_URL", "").strip()
    if redis_url:
        try:
            import redis  # type: ignore

            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return RedisRetrievalCache(client, ttl_seconds=ttl_seconds, prefix=prefix)
        except Exception:
            # Fall back to process-local memory cache if Redis is unavailable.
            pass

    return InMemoryRetrievalCache(ttl_seconds=ttl_seconds)


def normalize_cache_payload(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [normalize_cache_payload(item) for item in value]
    if isinstance(value, dict):
        return {str(key): normalize_cache_payload(item) for key, item in value.items()}
    return value


def build_search_cache_key(*, query: str, top_k: int, filters: dict[str, Any] | None, collection_name: str, model_name: str) -> str:
    payload = {
        "query": query.strip(),
        "top_k": top_k,
        "filters": normalize_cache_payload(filters or {}),
        "collection_name": collection_name,
        "model_name": model_name,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()