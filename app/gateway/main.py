import os
import socket
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException

from app.common.config import (
    INVENTORY_TIMEOUT_SECONDS,
    INVENTORY_URL,
)

from app.common.db import (
    create_order,
    database_is_ready,
    get_order,
)

from app.common.queue import (
    enqueue_order,
    redis_is_ready,
)

app = FastAPI(
    title="OpsForge Gateway API",
    version="0.1.0",
)


INVENTORY_URL = os.getenv(
    "INVENTORY_URL",
    "http://127.0.0.1:8001",
)


def inventory_is_ready() -> bool:
    try:
        response = httpx.get(
            f"{INVENTORY_URL}/health/ready",
            timeout=INVENTORY_TIMEOUT_SECONDS,
        )

        return response.status_code == 200

    except httpx.RequestError:
        return False


@app.get("/")
def root():
    return {
        "service": "gateway-api",
        "message": "OpsForge gateway is running",
    }


@app.get("/health/live")
def live():
    return {
        "status": "alive",
    }


@app.get("/health/ready")
def ready():
    dependencies = {
        "database": database_is_ready(),
        "redis": redis_is_ready(),
        "inventory": inventory_is_ready(),
    }

    is_ready = all(dependencies.values())

    if not is_ready:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "dependencies": dependencies,
            },
        )

    return {
        "status": "ready",
        "dependencies": dependencies,
    }


@app.get("/info")
def info():
    return {
        "service": "gateway-api",
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/check-inventory/{item_id}")
def check_inventory(item_id: str):
    try:
        response = httpx.get(
            f"{INVENTORY_URL}/inventory/{item_id}",
            timeout=1.0,
        )

        response.raise_for_status()

        return {
            "gateway": "ok",
            "inventory": response.json(),
        }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Inventory service timed out",
        )

    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=502,
            detail="Inventory service returned an error",
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Inventory service unavailable",
        )


@app.post(
    "/orders/{item_id}",
    status_code=202,
)
def create_new_order(item_id: str):
    try:
        inventory_response = httpx.get(
            f"{INVENTORY_URL}/inventory/{item_id}",
            timeout=1.0,
        )

        inventory_response.raise_for_status()

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Inventory service timed out",
        )

    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=502,
            detail="Inventory service returned an error",
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Inventory service unavailable",
        )

    order = create_order(item_id)

    enqueue_order(
        order["id"],
        order["item_id"],
    )

    return {
        "order": order,
        "inventory": inventory_response.json(),
        "background_job": "queued",
    }


@app.get("/orders/{order_id}")
def read_order(order_id: int):
    order = get_order(order_id)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    return order