import json
import os
from typing import Any, Optional
import redis
from log import logger


class CacheClient:
    def __init__(self, url: Optional[str] = None, ttl: int = 300):
        self.url = url or os.getenv("REDIS_URL", "redis://:redis123@localhost:6380/0")
        self.ttl = ttl
        try:
            self.client = redis.Redis.from_url(self.url, decode_responses=True, socket_timeout=3)
            self.client.ping()
            logger.info(f"redis connected: {self.url.split('@')[-1]}")
        except Exception as e:
            logger.warning(f"redis unavailable, fallback to no-op: {e}")
            self.client = None

    def get(self, key: str) -> Optional[Any]:
        if not self.client:
            return None
        try:
            v = self.client.get(key)
            return json.loads(v) if v else None
        except Exception as e:
            logger.error(f"redis get failed: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if not self.client:
            return
        try:
            self.client.set(key, json.dumps(value), ex=ttl or self.ttl)
        except Exception as e:
            logger.error(f"redis set failed: {e}")