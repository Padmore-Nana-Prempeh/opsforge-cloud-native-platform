# A1.4 — Gateway to Inventory Failure Propagation

| Scenario | Inventory state | Gateway result | Cause |
|---|---|---|---|
| Normal | healthy | HTTP 200 | dependency responded normally |
| Inventory stopped | no listener on 8001 | HTTP 503 | connection failure |
| Inventory latency = 2s | alive but exceeds 1s timeout | HTTP 504 | dependency timeout |
| Inventory error rate = 1 | HTTP service alive but returns 503 | HTTP 502 | downstream application error |

## Key Observation

The gateway process can remain alive while the request path is unhealthy.

Process existence therefore does not prove end-to-end service readiness.
