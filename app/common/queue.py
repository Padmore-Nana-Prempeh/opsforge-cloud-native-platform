import json
import os

import redis

from app.common.config import REDIS_URL


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://127.0.0.1:6379/0",
)

QUEUE_NAME = "opsforge:orders"


def get_redis():
    return redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_timeout=None,
        socket_connect_timeout=2,
    )

def redis_is_ready() -> bool:
    try:
        client = get_redis()
        return bool(client.ping())

    except redis.RedisError:
        return False


def enqueue_order(order_id: int, item_id: str) -> None:
    payload = {
        "order_id": order_id,
        "item_id": item_id,
    }

    client = get_redis()

    client.rpush(
        QUEUE_NAME,
        json.dumps(payload),
    )