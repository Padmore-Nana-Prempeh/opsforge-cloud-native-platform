# OpsForge Architecture

This directory contains the architectural documentation for OpsForge.

## Target Architecture

The architecture below represents the intended end state of OpsForge Track A.

![OpsForge Track A Architecture](docs/architecture/opsforge-track-a-architecture.png)

The platform is built incrementally. Components shown in this architecture do
not imply that they have already been implemented.

See [`docs/architecture`](docs/architecture/) for architectural details and
design decisions.

## Track A — Portfolio Core

The following diagram represents the target architecture for OpsForge Track A
and the intended end state for the `v1.0.0` release.

![OpsForge Track A Architecture](opsforge-track-a-architecture.png)

## Architecture Summary

Track A builds the platform incrementally from source code to a production-style
AWS EKS environment.

The primary delivery path is:

Developer → GitHub → GitHub Actions → GHCR → ECR → Argo CD → Amazon EKS

Key architectural principles include:

- continuous GitHub-based development
- immutable container images
- build once, promote instead of rebuild
- GitHub Container Registry as the initial CI registry
- Amazon ECR as the AWS runtime registry
- GitHub OIDC authentication to AWS
- Terraform/OpenTofu-managed infrastructure
- GitOps delivery through Argo CD
- a cost-optimized two-AZ AWS development environment
- a single EKS cluster with namespace-based dev, staging, and prod-like environments
- Prometheus, Grafana, Loki, and OpenTelemetry observability
- metrics-server for Kubernetes autoscaling
- explicit AWS cost controls and teardown verification

## Minimal Application

The application is intentionally small so that application development does not
distract from the DevOps learning objectives.

The workload contains:

- `gateway-api`
- `inventory-api`
- `worker`
- PostgreSQL
- Redis

The important operational path is:

```text
gateway-api
    │
    ├── synchronous request → inventory-api
    │
    ├── durable write → PostgreSQL
    │
    └── asynchronous job → Redis → worker → PostgreSQL
