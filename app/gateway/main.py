import os
import socket
from datetime import datetime, timezone

from fastapi import FastAPI


app = FastAPI(
    title="OpsForge Gateway API",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "service": "gateway-api",
        "message": "OpsForge gateway is running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


@app.get("/info")
def info():
    return {
        "service": "gateway-api",
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
