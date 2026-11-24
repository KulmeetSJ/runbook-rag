---
id: pf-cold-start
title: SLO breach right after a deploy (cold JVMs)
service: payflow
version: 1
updated: 2026-11-24
---
# Latency SLO breach right after a deploy (cold start)

## What was observed
In the lab, a freshly started stack sent 750 payments/s straight away broke the latency SLO badly: end-to-end p99 11.2 s and gateway p99 1.0 s. The same stack, warmed up through 50, 100, 200, 300, 400 and 500 payments/s first, held p99 0.50 s at 750/s. The JIT compiler has not optimised the hot paths yet, and every instance is doing that work at once.

## Steps if it happens after a deploy
1. Check deploy time against the start of the burn.
2. If the system is catching up (lag shrinking), wait; it usually settles within a few minutes.
3. If it is not catching up, roll back (`gitops-rollback`) rather than scaling, because new instances are also cold.

## Prevention
- Shift traffic gradually: canary steps (`gitops-canary-aborted` explains the analysis) rather than all at once.
- Warm up new instances with synthetic traffic before adding them to the load balancer.
- Avoid deploying at peak load.
