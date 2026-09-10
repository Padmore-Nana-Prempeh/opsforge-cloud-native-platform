# ADR-0002: Minimal Workload Topology

## Status

Accepted

## Context

OpsForge requires enough application behavior to expose meaningful DevOps,
Kubernetes, reliability, networking, state, and observability problems without
allowing application development to become the project.

## Decision

Track A uses three application processes and two supporting state services:

- gateway-api
- inventory-api
- worker
- PostgreSQL
- Redis

The primary synchronous path is:

client -> gateway-api -> inventory-api

The durable state path is:

gateway-api -> PostgreSQL

The asynchronous path is:

gateway-api -> Redis -> worker -> PostgreSQL

## Rationale

The topology deliberately provides:

- one public HTTP entry point
- one synchronous downstream dependency
- deterministic latency/error injection
- one durable database
- one background queue
- one non-HTTP worker
- observable dependency failures

This is sufficient for the Track A platform-learning objectives.

## Consequences

The application remains intentionally small.

After A2, normal business-feature development is frozen.

Later changes may introduce only:

- health behavior
- telemetry
- failure injection
- performance hooks
- security controls
- operational behavior required by the platform

## Known Limitations

The PostgreSQL write and Redis enqueue are not one atomic transaction.

If PostgreSQL succeeds and Redis enqueue fails, an order may exist without its
background job.

Track A records this limitation but does not implement a transactional outbox.

## Track B

Advanced resilience patterns may later attach to these existing failure
surfaces without redesigning the business workload.
