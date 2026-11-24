---
id: drift-state-lock
title: Terraform state locked
service: drift
version: 1
updated: 2026-11-19
---
# Terraform state is locked

State is stored in HCP Terraform (free tier) with execution mode **local**: plans and applies run on the laptop or in CI, HCP only stores state and locks it.

## Error
`Error acquiring the state lock ... workspace is already locked`

## Steps
1. Is another run in progress? Check running GitHub Actions jobs (the scheduled `drift.yml` takes about a minute) and other terminals.
2. If a run was cancelled mid-apply, the lock can remain. In HCP Terraform → workspace → Settings → Locking, check who holds it.
3. Only after confirming nothing is running: unlock in the HCP UI, or `terraform force-unlock <lock-id>`.

## Do not
Force-unlock while a run is actually applying: two concurrent applies can corrupt state.
