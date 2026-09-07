# OpsForge

**Production-Grade Cloud-Native GitOps Platform on AWS EKS**

OpsForge is an end-to-end DevOps, Platform Engineering, and SRE learning
project built incrementally from first principles.

The project progresses from local application execution through containers,
CI, Kubernetes, infrastructure as code, AWS EKS, GitOps, observability,
performance engineering, security, and reliability.

## Track

Current track:

**Track A — Portfolio Core**

Target release:

**v1.0.0**

## Learning Method

Every major capability follows:

Learn → Build → Observe → Break → Explain → Commit → Push

A phase is not complete simply because a command succeeds.

## Current Phase

### A0 — Bootstrap, Repository Discipline & Guardrails

Current objectives:

- establish the repository
- define engineering conventions
- establish Architecture Decision Records
- establish evidence collection
- establish cost-control guardrails
- prepare teardown and zero-resource verification workflows

## Core Track A Principles

1. Build the smallest application capable of producing meaningful operational failures.
2. Build container images once and promote immutable artifacts.
3. Prefer understanding constraints before optimizing them away.
4. Treat cost as an architectural constraint.
5. Never create AWS infrastructure without a tested teardown path.
6. Capture evidence for important engineering claims.
7. Maintain continuous, meaningful Git history.
8. Document architectural compromises explicitly.
9. Finish Track A as a reproducible `v1.0.0`.
10. Preserve enough state that Track B can resume months later.

## Cloud Safety Rule

No AWS infrastructure will be provisioned until:

- `runbooks/teardown.md` exists,
- automated teardown exists,
- zero-resource verification exists,
- AWS budget controls have been reviewed.

## Status

🚧 Track A in progress.
