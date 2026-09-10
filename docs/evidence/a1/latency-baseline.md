# A1.8 — Local Latency Baseline

## Scenario

Local host-level synchronous request:

client -> gateway-api -> inventory-api -> gateway-api -> client

## Conditions

- gateway-api: 127.0.0.1:8000
- inventory-api: 127.0.0.1:8001
- inventory injected latency: 0 seconds
- inventory injected error rate: 0
- requests: 100
- warm-up requests: 5
- environment: local macOS development machine

## Results

## A1 Local Latency Baseline

| Field | Value |
| --- | --- |
| Endpoint | `http://127.0.0.1:8000/check-inventory/baseline-item` |
| Requests | 100 |
| Min | 14.73 ms |
| P50 | 16.01 ms |
| P95 | 16.80 ms |
| Max | 29.88 ms |

## Interpretation

This is a local development baseline, not a production benchmark.

It exists so future container, Kubernetes and cloud measurements can be
compared against a documented starting point.
