---
id: gitops-canary-aborted
title: Argo Rollouts canary aborted
service: gitops
version: 2
updated: 2026-11-19
---
# Argo Rollouts canary aborted

## How the canary works
Steps: 20% of traffic → pause 1 min with analysis → 50% → analysis → 100%. The `AnalysisTemplate` queries Prometheus for the canary's HTTP 5xx rate and p95 latency. If the 5xx ratio is above 1% or p95 is above 500 ms in **2 of 3** measurements (30 s apart), the analysis fails and the rollout aborts automatically: traffic goes back to the stable ReplicaSet.

## Steps
1. `kubectl argo rollouts get rollout demo-app -n <env>` shows the step and status `Degraded` with `RolloutAborted`.
2. `kubectl get analysisrun -n <env>`, then `kubectl describe analysisrun <name>` to see the measured values.
3. Decide: a real regression → fix forward with a new commit. A false positive (for example no traffic, so the query returned NaN) → fix the AnalysisTemplate, then retry with `kubectl argo rollouts retry rollout demo-app -n <env>`.

## Drills
Rollback drills with a deliberately broken image are recorded in the platform repo (`measurements/`). The abort needs no manual action; the time to abort is set by the analysis interval and the 2-of-3 failure rule.
