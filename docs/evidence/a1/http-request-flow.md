# A1.2 — HTTP Request Flow

## Experiments

Successful request:

```bash
curl -v http://127.0.0.1:8000/health

Missing route:

```bash
curl -i http://127.0.0.1:8000/does-not-exist

Wrong HTTP method:

```bash
curl -i -X POST http://127.0.0.1:8000/health

### Observations
- A valid GET request returned HTTP 200.
- A nonexistent path returned HTTP 404.
- An unsupported method returned HTTP 405.
- When the Uvicorn process was stopped, the TCP connection itself failed.
- Client connections used temporary ephemeral source ports while the gateway remained bound to server port 8000.

### Failure Distinction

Server alive + route missing
    → HTTP 404

Server alive + method invalid
    → HTTP 405

Server process unavailable
    → TCP connection failure
