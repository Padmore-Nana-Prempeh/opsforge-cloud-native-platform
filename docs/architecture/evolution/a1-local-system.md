# A1 — Local Host Architecture

Phase A1 runs every component directly on the host.

```text
                              inventory-api
                                :8001
                                   ▲
                                   │ HTTP
                                   │
client ───────────────► gateway-api
                          :8000
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
          PostgreSQL                  Redis
             :5432                    :6379
                ▲                       │
                │                       │ queue
                │                       ▼
                └────────── worker


## Application Components

### gateway-api

`gateway-api` is the public HTTP entry point for the A1 workload.

It:

- listens on TCP port `8000`
- receives client HTTP requests
- calls `inventory-api` synchronously
- writes durable order state to PostgreSQL
- enqueues asynchronous work into Redis
- exposes liveness and readiness endpoints

The gateway is designed as stateless application compute. Durable business
state is not stored in gateway process memory.

### inventory-api

`inventory-api` is an internal synchronous HTTP dependency.

It:

- listens on TCP port `8001`
- provides inventory responses to `gateway-api`
- supports configurable latency injection
- supports configurable error injection
- exposes health endpoints

Its purpose is intentionally small. It exists primarily to provide a
controllable downstream dependency for networking, timeout,
failure-propagation, and observability experiments.

### worker

The worker is a long-running background process. Unlike `gateway-api` and
`inventory-api`, it does not expose an HTTP port.

Its runtime pattern is:

worker
  │
  ▼
Redis BLPOP
  │
  │ waits while queue is empty
  ▼
job received
  │
  ▼
update PostgreSQL
  │
  ▼
wait for next job

The worker consumes asynchronous jobs from Redis and updates order state in
PostgreSQL.

A worker can be temporarily unavailable while the gateway continues accepting
and queueing work, provided Redis remains available.

### PostgreSQL
PostgreSQL owns durable order state.

It listens locally on TCP port:5432

Order state remains available across gateway and worker process restarts because
the durable state is stored by PostgreSQL rather than inside application process
memory.

This establishes the architectural distinction:
gateway / inventory / worker
        =
application compute

PostgreSQL
        =
durable state

### Redis

Redis listens locally on TCP port:6379

Track A currently uses Redis for one specific purpose:

buffering asynchronous order-processing jobs between gateway-api and worker.

The asynchronous flow is:gateway
   │
   │ RPUSH
   ▼
Redis queue
   │
   │ BLPOP
   ▼
worker

This decouples request acceptance from background processing.

If the worker is unavailable but Redis remains healthy, jobs can wait in the
queue until the worker returns.

...
...
...
...

### Failure Characteristics
The A1 architecture intentionally exposes several different failure classes.
gateway stopped
→ no listener on :8000
→ client TCP connection fails

inventory stopped
→ gateway remains alive
→ synchronous dependency request fails

PostgreSQL stopped
→ gateway may remain live
→ durable-state operations fail
→ readiness becomes false

Redis stopped
→ gateway may remain live
→ asynchronous enqueue fails
→ readiness becomes false

worker stopped
→ gateway may continue accepting work
→ Redis queue grows
→ orders remain unfinished until worker returns
