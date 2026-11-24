---
id: inc-2026-11-19-canary-drill
title: "Drill notes: canary rollback drills"
service: gitops
version: 1
updated: 2026-11-19
---
# Drill notes 2026-11-19: canary rollback drills

Drill lead: Sam Whitfield (sam.whitfield@example.com). Observer: Grace Adeyemi, phone 07700 900456.

Five drills: a release that returns HTTP 500 on 30% of requests was pushed through the normal pipeline to staging.
- In every drill the AnalysisRun failed at the 20% step and Argo Rollouts aborted, returning traffic to the stable ReplicaSet without a human.
- Lesson 1: during a drill, do not push to the app repo. Its CI commits a dev deploy to the platform repo and changes what Argo CD is syncing.
- Lesson 2: with no traffic, the Prometheus query returns no data and the analysis can be inconclusive. Drills run a load generator first.
