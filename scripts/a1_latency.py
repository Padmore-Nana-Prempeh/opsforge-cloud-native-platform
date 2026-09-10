import math
import os
import statistics
import time

import httpx


URL = os.getenv(
    "A1_LATENCY_URL",
    "http://127.0.0.1:8000/check-inventory/baseline-item",
)

REQUESTS = int(
    os.getenv(
        "A1_LATENCY_REQUESTS",
        "100",
    )
)

WARMUP_REQUESTS = 5


def percentile(values, percentile_value):
    ordered = sorted(values)

    index = math.ceil(
        percentile_value * len(ordered)
    ) - 1

    return ordered[index]


def main():
    latencies_ms = []

    with httpx.Client(timeout=3.0) as client:

        for _ in range(WARMUP_REQUESTS):
            response = client.get(URL)
            response.raise_for_status()

        for _ in range(REQUESTS):

            start = time.perf_counter()

            response = client.get(URL)

            elapsed = (
                time.perf_counter() - start
            ) * 1000

            response.raise_for_status()

            latencies_ms.append(elapsed)

    p50 = statistics.median(
        latencies_ms
    )

    p95 = percentile(
        latencies_ms,
        0.95,
    )

    minimum = min(latencies_ms)
    maximum = max(latencies_ms)

    print("OpsForge A1 local latency baseline")
    print("--------------------------------")
    print(f"URL:      {URL}")
    print(f"Requests: {REQUESTS}")
    print(f"Min:      {minimum:.2f} ms")
    print(f"P50:      {p50:.2f} ms")
    print(f"P95:      {p95:.2f} ms")
    print(f"Max:      {maximum:.2f} ms")


if __name__ == "__main__":
    main()
