# A1.5 — PostgreSQL Durable State

## Objective

Demonstrate the difference between stateless application compute and durable
database state.

## Runtime

The local system used:

- gateway-api on TCP 8000
- inventory-api on TCP 8001
- PostgreSQL on TCP 5432

## Persistence Experiment

1. Created an order through gateway-api.
2. Confirmed the row existed in PostgreSQL.
3. Terminated gateway-api.
4. Restarted gateway-api.
5. Retrieved the same order successfully.

## Observation

Application process termination did not delete previously committed order
state because that state was owned by PostgreSQL rather than gateway process
memory.

## Dependency Failure Experiment

PostgreSQL was stopped while gateway-api remained alive.

The gateway process could still respond to its liveness endpoint, but
database-dependent operations failed.

## Key Model

```text
gateway-api
    =
stateless compute

PostgreSQL
    =
durable state


