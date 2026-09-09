import json
import time

from app.common.db import update_order_status
from app.common.queue import QUEUE_NAME, get_redis


def process_job(job: dict) -> None:
    order_id = job["order_id"]

    print(f"Processing order {order_id}")

    update_order_status(
        order_id,
        "processing",
    )

    time.sleep(2)

    update_order_status(
        order_id,
        "completed",
    )

    print(f"Completed order {order_id}")


def main() -> None:
    redis_client = get_redis()

    print("OpsForge worker started")
    print(f"Waiting for jobs on queue: {QUEUE_NAME}")

    while True:
        _, payload = redis_client.blpop(
            QUEUE_NAME,
            timeout=0,
        )

        job = json.loads(payload)

        process_job(job)


if __name__ == "__main__":
    main()