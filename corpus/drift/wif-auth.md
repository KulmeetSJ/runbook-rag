---
id: drift-wif-auth
title: GitHub Actions cannot authenticate to GCP (WIF)
service: drift
version: 1
updated: 2026-11-19
---
# GitHub Actions cannot authenticate to GCP (Workload Identity Federation)

The workflow exchanges its GitHub OIDC token for a short-lived GCP token. There are no service account keys.

## Errors and causes
- `Permission 'iam.serviceAccounts.getAccessToken' denied`: the principal for this repo is missing `roles/iam.workloadIdentityUser` on the service account. The binding member must match the attribute, e.g. `principalSet://iam.googleapis.com/projects/<number>/locations/global/workloadIdentityPools/github/attribute.repository/<owner>/<repo>`.
- `The given credential is rejected by the attribute condition`: the provider's attribute condition (for example `assertion.repository_owner == '<owner>'`) does not match. A forked repo or a renamed repo fails here, which is intended.
- `Unable to acquire impersonated credentials`: the workflow lacks `permissions: id-token: write`.

## Steps
1. Check the workflow has `id-token: write`.
2. `gcloud iam workload-identity-pools providers describe github --location=global --workload-identity-pool=github` and compare the condition with the repo.
3. Check the service account's IAM policy for the `workloadIdentityUser` binding.
