---
id: pf-success-burn
title: PaymentSuccessBudgetFastBurn page
service: payflow
version: 1
updated: 2026-11-20
---
# PaymentSuccessBudgetFastBurn (page)

SLO: 99.9% of valid payments processed (completed or rejected by a business rule) without being dead-lettered. Budget: 0.1%. Page at 14.4x over 1 h and 5 m.

Business rejections (insufficient funds, currency mismatch) are **good** events: the system did its job. Only `payments_dead_lettered_total{kind="exhausted"}` counts as bad. Poison messages do not count.

## Steps
1. Find what is failing: `/admin/dlt` and group by `kafka_exception-message` (see `pf-dlt-growth`).
2. Fix the dependency.
3. Replay (see `pf-dlt-replay`).

Because the budget is only 0.1%, about 2 dead letters per 100 payments is already a ~20x burn and pages.
