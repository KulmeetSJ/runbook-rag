---
id: pf-gateway-503
title: Gateway returning 503 on POST /payments
service: payflow
version: 1
updated: 2026-11-21
---
# Gateway returning 503 on POST /payments

The gateway returns 503 when the Kafka send does not complete within `delivery.timeout.ms` (10 s). The payment was **not** accepted, and the client should retry with the same `Idempotency-Key`. Retrying with the same key is safe: the processor deduplicates on the event ID derived from it.

## Common causes
1. **Broker failover in progress** (most common). A burst of 503s lasting 10–20 s right after a broker died. See `pf-broker-down`.
2. **Fewer than 2 in-sync replicas.** Sustained 503s. `acks=all` cannot be satisfied. Restore brokers.
3. **Gateway thread pool exhausted.** p99 latency climbs before the 503s start; the load generator's virtual users are all blocked on sends.

## Tuning note
In the broker-kill chaos test, 72 requests got 503 because the 10 s timeout is barely longer than the ~10 s failover. Raising `delivery.timeout.ms` to 30 s would turn most of those into slow 202s. The trade-off is that clients wait longer before they see a failure.
