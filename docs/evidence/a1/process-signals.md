# A1.3 — Process and Signal Experiments

## Objective

Understand process relationships, foreground/background jobs, and Unix
termination signals using the OpsForge gateway.

## Process Inspection

The gateway process was inspected using:

```bash
ps -p <PID> -o pid,ppid,pgid,stat,%cpu,%mem,command

The gateway had its own PID and a parent process associated with the shell
that launched it.

- SIGINT
Pressing Ctrl+C sent an interrupt signal to the foreground server.
Uvicorn performed a graceful shutdown.

- SIGTERM
The gateway was terminated using: kill -TERM <PID>
Uvicorn received the termination request and performed an orderly shutdown.

- SIGKILL
The gateway was forcefully terminated using:kill -KILL <PID>
Unlike SIGTERM, the process did not receive an opportunity to perform graceful shutdown behavior.

- Background Process
The gateway was started with:uvicorn services.gateway.main:app --host 127.0.0.1 --port 8000 &
The shell returned immediately while the gateway continued running.
$! identified the most recently started background process.

- Key Distinction
SIGTERM
   ↓
application can react
   ↓
graceful shutdown

SIGKILL
   ↓
forced operating-system termination

- Kubernetes Relevance

Container orchestrators normally attempt graceful termination before forcing
process termination after a configured grace period.

Understanding process signals is therefore necessary for reasoning about
Pod termination and application shutdown behavior.

---
