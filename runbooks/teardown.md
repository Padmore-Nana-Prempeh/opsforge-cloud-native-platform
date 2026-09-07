# OpsForge Teardown Runbook

## Purpose

OpsForge uses paid cloud infrastructure during later Track A phases.

The default development operating model is:

Provision → Learn → Test → Collect Evidence → Destroy → Verify Zero

Cloud infrastructure should not remain running simply because a learning
session has ended.

## Pre-AWS Rule

No Terraform infrastructure may be applied until the teardown workflow and
zero-resource verification process have been reviewed.

## Planned Teardown Workflow

Later phases will implement:

```bash
make destroy
make verify-zero
