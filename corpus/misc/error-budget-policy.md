---
id: misc-error-budget-policy
title: Error budget policy
service: payflow
version: 2
updated: 2026-11-20
---
# Error budget policy

Budgets are measured over 28 days: latency SLO 1%, success SLO 0.1%.

| Budget left | What changes |
|---|---|
| more than 50% | Normal releases. |
| 25–50% | Releases continue; every incident gets a postmortem with action items. |
| less than 25% | Freeze feature releases. Only fixes, security patches and reliability work go to prod. |
| exhausted | Freeze until the budget is positive again; the top reliability action item is staffed first. |

Exceptions to a freeze need the payments owner's approval, recorded in the release PR.

Note: on a lab stack with little history the budget numbers are extreme (for example −3208% after a 4-minute incident with 25 minutes of history). Budgets only mean something over real traffic volumes.
