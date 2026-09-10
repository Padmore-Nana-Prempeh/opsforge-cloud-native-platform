import os


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://localhost/opsforge",
)

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://127.0.0.1:6379/0",
)

INVENTORY_URL = os.getenv(
    "INVENTORY_URL",
    "http://127.0.0.1:8001",
)

INVENTORY_TIMEOUT_SECONDS = float(
    os.getenv(
        "INVENTORY_TIMEOUT_SECONDS",
        "1.0",
    )
)
