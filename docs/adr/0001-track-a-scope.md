# ADR-0001: Track A Scope

## Status

Accepted

## Context

OpsForge could expand into a very large cloud-native platform involving
multi-cluster Kubernetes, advanced chaos engineering, service meshes,
multi-region disaster recovery, internal developer platforms, and advanced
supply-chain security.

Attempting all of these capabilities in the initial project would increase
cost, complexity, and completion risk.

## Decision

Track A will build a focused production-style platform ending at version
v1.0.0.

Track A will cover:

- systems fundamentals
- minimal application architecture
- containers
- continuous integration
- Kubernetes
- Helm
- infrastructure as code
- AWS EKS
- GitOps
- observability
- load testing and autoscaling
- baseline security
- reliability and recovery
- operational documentation and evidence

Advanced capabilities will remain extension points for Track B.

## Consequences

Track A remains achievable while still demonstrating meaningful DevOps,
cloud, platform, and SRE engineering.

Some production concerns will intentionally remain outside the scope of
v1.0.0.

## Track B

Track B may later extend the same platform with:

- multi-cluster architecture
- advanced supply-chain security
- progressive delivery
- advanced autoscaling
- SLO and error-budget engineering
- advanced networking
- chaos engineering
- disaster recovery
- internal developer platform capabilities
