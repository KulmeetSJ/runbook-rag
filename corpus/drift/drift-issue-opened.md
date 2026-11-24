---
id: drift-issue-opened
title: Drift detected issue opened by drift.yml
service: drift
version: 2
updated: 2026-11-19
---
# "Drift detected" issue opened by the drift workflow

The `drift.yml` workflow runs `terraform plan -detailed-exitcode` every 6 hours against the sandbox GCP project. Exit code 2 means the live resources differ from the Terraform configuration. The workflow then opens (or updates) one GitHub issue labelled `drift` with the plan summary, and closes it automatically on the next clean run.

## Steps
1. Open the issue and read the plan: which resources change, and is it `update in-place`, `replace`, or `destroy`?
2. Decide who is right:
   - **Someone changed GCP by hand** (console click, `gcloud`). Either revert it by running `terraform apply`, or, if the change was intended, put it into the Terraform code through a PR.
   - **The code changed but was not applied.** Apply it through the normal pipeline.
3. IAM drift is the most sensitive: an extra binding such as `roles/owner` added by hand is a security finding, not just drift. Escalate to the security owner before reverting so it can be investigated.

## Measured
In the induced-drift test, 7 of 7 manual changes were detected, with a median time-to-detect of 26 s from workflow start.
