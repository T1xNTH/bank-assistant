"""Redis-backed token buckets shared across API and worker processes."""

from __future__ import annotations

import math
import time

from redis import Redis
from redis.exceptions import RedisError, WatchError


class TokenBucket:
    def __init__(self, connection: Redis, key: str, rpm: int, capacity: int = 1):
        if rpm < 1 or capacity < 1:
            raise ValueError("Token bucket limits must be positive")
        self.connection, self.key = connection, key
        self.rate, self.capacity = rpm / 60, capacity

    def take(self) -> float:
        """Consume one token atomically, or return seconds until one is available.

        Redis TIME avoids clock skew across hosts. Failed attempts do not consume
        tokens; idle bucket keys expire once the bucket would be full again.
        """
        for _ in range(20):
            with self.connection.pipeline() as pipe:
                try:
                    pipe.watch(self.key)
                    seconds, micros = pipe.time()
                    now = seconds + micros / 1_000_000
                    saved = pipe.hgetall(self.key)
                    tokens = float(saved.get(b"tokens", self.capacity))
                    updated = float(saved.get(b"updated", now))
                    tokens = min(self.capacity, tokens + max(0, now - updated) * self.rate)
                    delay = max(0.0, (1 - tokens) / self.rate)
                    if delay:
                        return delay
                    pipe.multi()
                    pipe.hset(self.key, mapping={"tokens": tokens - 1, "updated": now})
                    pipe.expire(self.key, max(1, math.ceil(self.capacity / self.rate)))
                    pipe.execute()
                    return 0.0
                except WatchError:
                    continue
        raise RedisError("Rate limiter busy")

    def acquire(self) -> None:
        while delay := self.take():
            time.sleep(delay)
