---
id: gitops-prod-approval
title: Production deploy waiting for approval
service: gitops
version: 1
updated: 2026-11-19
---
# Production deploy is waiting for approval

Promotion to prod uses a GitHub Environment named `prod` with required reviewers. The workflow pauses at the `promote-prod` job until a reviewer approves.

## Steps for the approver
1. Check staging: the same image SHA has been running in staging and the canary analysis passed.
2. Check the error budget: under the error budget policy, if less than 25% of the latency budget is left, only fixes are approved.
3. Approve in the Actions run → Review deployments.

## Lead time
Measured commit-to-prod lead time (3 runs) was dominated by this wait. The automated part takes minutes.
