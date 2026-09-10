# A1.6 — Redis Queue and Asynchronous Worker

## Objective

Demonstrate asynchronous processing using Redis as a queue between gateway-api
and a background worker.

## Normal Flow

```text
client
  ↓
gateway-api
  ↓
inventory-api
  ↓
PostgreSQL: order created
  ↓
Redis: job queued
  ↓
HTTP 202 returned

worker
  ↓
Redis job consumed
  ↓
PostgreSQL: processing
  ↓
PostgreSQL: completed

## Worker-Down Experiment

The worker was stopped while Redis remained available.

A new order was successfully persisted and queued.

The HTTP request returned before the worker was available.

Redis queue depth increased.

After restarting the worker, the queued job was consumed and the order
transitioned to completed.

## Redis-Down Experiment

Redis was stopped while gateway-api remained alive.

Inventory validation and PostgreSQL access were still possible, but queue
submission failed.

This exposed Redis as a required dependency for the current create-order
workflow.

## Synchronous vs Asynchronous Failure

| Dependency | Type | Failure effect |
| --- | --- | --- |
| inventory-api | synchronous | request fails immediately |
| Redis | enqueue dependency | request cannot queue background work |
| worker | asynchronous consumer | request may succeed; work waits in queue |
| PostgreSQL | durable state | database-dependent operations fail |

## Known Limitation

The current sequence writes the order to PostgreSQL before enqueueing Redis.

If the database write succeeds but Redis enqueue fails, durable state may exist
without a corresponding background job.

Track A records this limitation but does not introduce a transactional outbox.
