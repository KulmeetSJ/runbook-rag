---
id: pf-duplicates
title: Suspected duplicate payment
service: payflow
version: 1
updated: 2026-11-20
---
# Suspected duplicate payment

## How duplicates are prevented
1. **Client retries:** the gateway derives the event ID from the `Idempotency-Key` header, so a retry produces the same event ID.
2. **Kafka redelivery:** the processor inserts the event ID into `processed_events` (primary key) in the same transaction as the ledger write. A second delivery hits the key, the transaction is skipped, and the metric `payments_processed_total{outcome="duplicate"}` goes up.
3. The producer is idempotent (`enable.idempotence=true`), so broker retries do not duplicate records within a partition.

## Investigation
1. `SELECT payment_id, idempotency_key, status, accepted_at FROM payments WHERE from_account = '<acct>' ORDER BY accepted_at DESC LIMIT 20;`
2. Two rows with **different** idempotency keys and the same amount are two payments from the client's point of view. That is not a platform duplicate; the client sent two requests with different keys.
3. Two ledger entry pairs for one `payment_id` would be a real bug. It should be impossible because of the primary key. Escalate immediately.
