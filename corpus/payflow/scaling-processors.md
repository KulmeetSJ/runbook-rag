---
id: pf-scaling
title: Scaling payment processors
service: payflow
version: 2
updated: 2026-11-24
---
# Scaling payment processors

## Rules
- The topic `payments.initiated` has **6 partitions**. Each partition is consumed by at most one consumer in the group, so more than 6 consumer threads in total gives no extra throughput: the 7th instance sits idle (shown in the consumer-scaling demo, 1 → 3 → 6 → 7 → 3).
- Threads per instance are set by `LISTENER_CONCURRENCY` (default 1). Instances × concurrency should not exceed 6.
- Ordering is per account (messages are keyed by `accountId`), so parallelism never reorders payments for the same account.

## Capacity reference (lab laptop, 3 processors, 1 thread each)
The knee is between 750 and 1,000 payments/s. At 750/s end-to-end p99 is about 0.5 s; at 1,000/s lag starts growing. The limit is CPU on the laptop, not the database.

## How to scale
`docker compose up -d --scale payment-processor=6`. Expect one cooperative rebalance; only moved partitions pause.

## When scaling will not help
If the database is slow (`pf-db-latency`) or the pool is exhausted (`pf-hikari-exhausted`), more consumers add load to the bottleneck.
