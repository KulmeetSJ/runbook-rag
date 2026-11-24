---
id: pf-dlt-growth
title: Dead-letter topic is growing
service: payflow
version: 2
updated: 2026-11-20
---
# Dead-letter topic (payments.initiated-dlt) is growing

Alerts: `PaymentSuccessBudgetFastBurn` (page) or `PaymentSuccessBudgetSlowBurn` (ticket). Metric: `payments_dead_lettered_total{kind}`.

## Two kinds of dead letter
- `kind="exhausted"`: a valid payment failed every attempt (3 blocking tries, then retry topics at 1 s, 2 s and 4 s). These count against the success SLO (99.9%).
- `kind="poison"`: the message could not be deserialised or failed validation (for example a tampered `eventId`). It goes to the DLT on attempt 1 without blocking the partition. Poison messages raise their own ticket and do **not** burn the success SLO.

## Triage
1. `curl -s localhost:8081/admin/dlt?limit=20 | jq` lists the newest DLT records with headers `kafka_exception-message`, `kafka_original-topic`, `kafka_original-offset`. Note: Spring Kafka's retry-topic headers are `kafka_exception-*` and `kafka_original-*`, not `kafka_dlt-*`.
2. Group by exception message. One repeated exception = one cause.
3. If the exception is a downstream failure (database, network), fix that first. Replaying into a broken dependency only refills the DLT.

## Next step
Once the cause is fixed, replay: see `pf-dlt-replay`.
