# A1.7 — Liveness, Readiness and Dependency Health

## Objective

Distinguish process liveness from ability to serve the primary OpsForge
workflow.

## Healthy State

With PostgreSQL, Redis and inventory-api available:

- `/health/live` returned HTTP 200
- `/health/ready` returned HTTP 200

## Dependency Failure Matrix

| Failure | Liveness | Readiness | Reason |
|---|---:|---:|---|
| PostgreSQL stopped | 200 | 503 | durable state unavailable |
| Redis stopped | 200 | 503 | queue unavailable |
| inventory-api stopped | 200 | 503 | synchronous dependency unavailable |
| gateway stopped | connection fails | connection fails | no process listening on port 8000 |

## Key Principle

Liveness answers whether the gateway process/application is alive.

Readiness answers whether the gateway instance should currently receive
traffic for its required workload.

A live process is not necessarily a ready service.

## Configuration

Runtime addresses and timeout values are supplied through environment
variables rather than hardcoded deployment-specific configuration.

This prepares the application for Docker Compose and Kubernetes configuration
in later phases.
