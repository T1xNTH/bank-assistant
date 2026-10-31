"""RQ worker with token-bucket rate limit and retry/backoff on 429.

Owner: B — Epic E-009. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

import math
import os
import socket
import sys
import time
from collections.abc import Callable
from datetime import timezone
from typing import TypeVar

from redis import Redis
from redis.exceptions import RedisError
from rq import Worker
from rq.serializers import JSONSerializer

from app.queue.limits import TokenBucket

QUEUE_NAMES = ("ask-high", "ask-default", "ask")  # Drain pre-T-025 jobs last.
T = TypeVar("T")


def positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


def positive_float(name: str, default: float) -> float:
    value = float(os.getenv(name, str(default)))
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive and finite")
    return value


def run_with_policy(action: Callable[[], T], connection: Redis) -> T:
    """Bound worker execution attempts globally, retry only explicit upstream 429s.

    A one-token bucket avoids an initial RPM-sized burst. Backoff is bounded by
    retry count; every retry re-acquires a token, including across workers.
    """
    from app.llm import LLMRateLimitError

    bucket = TokenBucket(connection, "ask:worker:rate", positive_int("WORKER_RPM", 60))
    retries = positive_int("WORKER_MAX_ATTEMPTS", 4)
    backoff = positive_float("WORKER_BACKOFF_SECONDS", 1)
    for attempt in range(retries):
        bucket.acquire()
        try:
            return action()
        except LLMRateLimitError:
            if attempt == retries - 1:
                raise
            time.sleep(min(60, backoff * 2**attempt))
    raise RuntimeError("Worker attempt limit reached")


def main() -> None:
    # Keep the separate healthcheck process free of Presidio/LLM imports.
    from app.log_config import configure_logging

    configure_logging()
    # RQ uses blocking dequeue: its socket timeout must exceed dequeue timeout.
    connection = Redis.from_url(
        os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"), socket_connect_timeout=2,
    )
    # RQ's random name avoids collisions with registrations left by SIGKILL/OOM.
    Worker(QUEUE_NAMES, connection=connection, serializer=JSONSerializer).work()


def healthy() -> bool:
    """Check this container's registration and heartbeat, never another replica's.

    RQ can block idle dequeue for 405s, so allow its default worker TTL plus
    heartbeat grace. Busy workers heartbeat from the monitoring parent. Match
    hostname and a live PID because each startup receives a new RQ name.
    """
    connection = Redis.from_url(
        os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"), socket_connect_timeout=2, socket_timeout=2,
    )
    try:
        seconds, micros = connection.time()
        for worker in Worker.all(connection=connection, serializer=JSONSerializer):
            if worker.hostname != socket.gethostname() or not worker.pid:
                continue
            if worker.last_heartbeat is None or worker.get_state() == "stopped":
                continue
            try:
                os.kill(worker.pid, 0)
            except OSError:
                continue
            age = seconds + micros / 1_000_000 - worker.last_heartbeat.replace(tzinfo=timezone.utc).timestamp()
            if 0 <= age <= worker.worker_ttl + 60:
                return True
        return False
    except RedisError:
        return False
    finally:
        connection.close()


if __name__ == "__main__":
    if "--healthcheck" in sys.argv[1:]:
        sys.exit(0 if healthy() else 1)
    main()

