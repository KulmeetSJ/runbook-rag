---
id: gitops-rollback
title: Rolling back a release
service: gitops
version: 2
updated: 2026-11-19
---
# Rolling back a release

## Preferred: revert in Git
1. Find the deploy commit in the platform repo (CI writes `deploy(<env>): demo-app <sha>`).
2. `git revert <commit>` and push (prod needs a PR with approval).
3. Argo CD syncs the previous image tag. With the canary strategy, the rollback itself also goes through the steps, unless you abort first.

## Emergency: abort the rollout
`kubectl argo rollouts abort demo-app -n prod` sends all traffic back to the stable ReplicaSet at once. Then revert in Git so Argo CD does not redeploy the bad version.

## Do not
- Do not push to the app repo during a rollback drill: its CI commits a new dev deploy and moves the target.
- Do not `kubectl set image` by hand; self-heal will undo it.
