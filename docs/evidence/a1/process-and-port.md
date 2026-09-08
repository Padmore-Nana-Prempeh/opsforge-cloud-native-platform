# A1.1 — Gateway Process and Port Evidence

## Experiment

Started the OpsForge gateway directly with Uvicorn.

```bash
uvicorn services.gateway.main:app --host 127.0.0.1 --port 8000

## Observations
The operating system created a running Python/Uvicorn process with a unique PID.

The process opened a TCP listening socket at:127.0.0.1:8000

The process was verified using:
 ps
lsof
curl
After terminating the process, port 8000 no longer had a listening socket and
HTTP requests failed.
