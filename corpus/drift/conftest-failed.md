---
id: drift-conftest-failed
title: PR blocked by Conftest policy
service: drift
version: 1
updated: 2026-11-19
---
# Pull request blocked by a Conftest policy

On every PR, CI runs `terraform plan`, converts it to JSON, and checks it with Conftest (Rego policies in `policy/`).

## Common denials
- `public BigQuery dataset`: an access entry with `allAuthenticatedUsers` or `allUsers`.
- `primitive role`: a binding to `roles/owner`, `roles/editor` or `roles/viewer`. Use a predefined or custom role instead.
- `service account key`: `google_service_account_key` resources are not allowed; use Workload Identity Federation (`drift-wif-auth`).
- `missing labels`: resources must carry `owner` and `env` labels.

## Steps
1. Read the Conftest output in the job log; each failure names the resource address and the rule.
2. Change the Terraform code. Policies are not bypassed per PR.
3. If the policy is wrong, change the policy in its own PR with a test in `policy/*_test.rego`.
