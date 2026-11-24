---
id: drift-gcp-429
title: Terraform google provider returns HTTP 429 locally
service: drift
version: 1
updated: 2026-11-19
---
# Terraform fails locally with HTTP 429 (quota exceeded)

## Cause
With a gcloud **user** access token, the google provider bills API quota to gcloud's own shared OAuth client project. That project is shared by everyone, so it runs out of quota quickly and returns 429.

## Fix
In the provider block set `user_project_override = true` and `billing_project = "<your project>"`, so quota is charged to your own project. Then run with a fresh token:
```bash
GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token) terraform plan
```
In CI this does not happen: Workload Identity Federation gives a service-account identity whose quota project is the sandbox project.
