# ADR-0002: Repository and Git Workflow

## Status

Accepted

## Context

OpsForge is a long-running learning and engineering project that will evolve
through application development, containers, CI, Kubernetes, AWS,
observability, security, and reliability work.

The repository must preserve a useful engineering history without introducing
unnecessary workflow complexity.

## Decision

OpsForge will use:

- `main` as the stable integration branch
- short-lived branches for meaningful units of work
- conventional-style commit prefixes
- continuous GitHub pushes
- phase-specific evidence
- architecture evolution documentation
- ADRs for significant design decisions

Examples of branch names:

- `feat/a1-gateway-api`
- `build/a2-containers`
- `infra/a5-eks`
- `obs/a7-prometheus`
- `perf/a8-hpa`
- `fix/<description>`

## Commit Categories

- `feat:` application capability
- `fix:` bug correction
- `test:` testing
- `build:` packaging or container builds
- `ci:` continuous integration
- `infra:` infrastructure
- `k8s:` Kubernetes
- `gitops:` Argo CD and deployment state
- `obs:` observability
- `security:` security
- `perf:` performance
- `docs:` documentation
- `chore:` repository maintenance

## Evidence

Important engineering claims should be supported by reproducible evidence
under `docs/evidence`.

## Consequences

The repository history becomes part of the final project portfolio.

This approach adds modest process overhead but avoids the complexity of a
full GitFlow model.
