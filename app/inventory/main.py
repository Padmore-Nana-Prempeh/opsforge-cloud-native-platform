import os
import random
import time

from fastapi import FastAPI, HTTPException


app = FastAPI(
    title="OpsForge Inventory API",
    version="0.1.0",
)


def get_latency_seconds() -> float:
    return float(os.getenv("INVENTORY_LATENCY_SECONDS", "0"))


def get_error_rate() -> float:
    return float(os.getenv("INVENTORY_ERROR_RATE", "0"))


@app.get("/")
def root():
    return {
        "service": "inventory-api",
        "message": "OpsForge inventory is running",
    }


@app.get("/health/live")
def live():
    return {
        "status": "alive",
    }


@app.get("/health/ready")
def ready():
    return {
        "status": "ready",
    }


@app.get("/inventory/{item_id}")
def get_inventory(item_id: str):
    latency = get_latency_seconds()
    error_rate = get_error_rate()

    if latency > 0:
        time.sleep(latency)

    if random.random() < error_rate:
        raise HTTPException(
            status_code=503,
            detail="Injected inventory failure",
        )

    return {
        "item_id": item_id,
        "available": True,
        "quantity": 100,
    }
