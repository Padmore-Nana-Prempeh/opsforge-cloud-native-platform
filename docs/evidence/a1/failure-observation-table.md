# A1 — Failure Observation Table

| Scenario | Visible symptom | Diagnostic command | Root cause | Recovery |
|---|---|---|---|---|
| Gateway stopped | curl connection refused on :8000 | `lsof -nP -iTCP:8000 -sTCP:LISTEN` | no process owns listening socket | restart gateway |
| Inventory stopped | gateway returns 503 | `lsof -nP -iTCP:8001 -sTCP:LISTEN` | synchronous dependency unavailable | restart inventory |
| Inventory latency > gateway timeout | gateway returns 504 | inspect inventory config + gateway logs | dependency exceeds timeout budget | remove latency/fix dependency |
| Inventory injected error | gateway returns 502 | direct curl to inventory | downstream service returns error | restore healthy inventory behavior |
| PostgreSQL stopped | live=200, ready=503; DB routes fail | `lsof -nP -iTCP:5432 -sTCP:LISTEN` | durable-state dependency unavailable | restart PostgreSQL |
| Redis stopped | live=200, ready=503; enqueue fails | `redis-cli ping` | queue dependency unavailable | restart Redis |
| Worker stopped | requests may queue; order remains incomplete | `redis-cli LLEN opsforge:orders` | queue consumer unavailable | restart worker |
| Redis queue waiting normally | worker appears idle | `ps` + `redis-cli LLEN` | worker blocked correctly on BLPOP | no recovery required |
