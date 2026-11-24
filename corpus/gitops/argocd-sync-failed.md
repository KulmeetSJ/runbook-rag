---
id: gitops-sync-failed
title: Argo CD application sync failed
service: gitops
version: 2
updated: 2026-11-19
---
# Argo CD application sync failed

Applications: `demo-app-dev`, `demo-app-staging`, `demo-app-prod`, generated from the Helm chart in the platform repo.

## Triage
1. `argocd app get demo-app-<env>` shows the failing resource and the message.
2. Common messages:
   - `admission webhook "validate.kyverno.svc" denied the request`: a policy blocked the manifest. See `gitops-kyverno-latest` and `gitops-kyverno-limits`.
   - `ImagePullBackOff` after sync: the image tag in `values-<env>.yaml` does not exist in the registry. Check the CI run that should have pushed it.
   - `the server could not find the requested resource`: a CRD (for example `Rollout` from Argo Rollouts) is not installed in that cluster.
3. `argocd app diff demo-app-<env>` shows what Argo CD is trying to apply.

## Fix
Fix the manifest in Git and let Argo CD sync. Do not `kubectl apply` by hand: Argo CD's self-heal will revert manual changes, and the change would not be in Git history.
