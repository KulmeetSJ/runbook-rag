---
id: gitops-out-of-sync
title: Argo CD shows OutOfSync without a commit
service: gitops
version: 1
updated: 2026-11-19
---
# Argo CD shows OutOfSync but nobody committed

## Meaning
The live cluster differs from Git. Someone changed a resource by hand (`kubectl edit`, `kubectl scale`), or a controller mutates a field Argo CD tracks.

## Steps
1. `argocd app diff demo-app-<env>`: which fields differ?
2. Manual change: self-heal is enabled, so Argo CD reverts it within about 3 minutes. If the change was an emergency fix, commit it to Git first, or it will be undone.
3. Controller-managed field (for example `replicas` owned by an autoscaler, or a `caBundle` injected by a webhook): add it to `ignoreDifferences` in the Application spec.

## Do not
Turn off self-heal to stop the "flapping". That hides drift instead of fixing it.
