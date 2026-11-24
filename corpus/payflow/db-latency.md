---
id: pf-db-latency
title: PostgreSQL slow, payments stalling
service: payflow
version: 3
updated: 2026-11-24
---
# PostgreSQL is slow and payments are stalling

## Symptoms
- Gateway looks healthy: 202s at normal latency (it never touches the database).
- Committed payments per second collapse; lag grows on **every** partition.
- `PaymentLatencyBudgetFastBurn` pages. Since the SLI fix it fires about 11 minutes after the stall starts.

## Why throughput collapses so far
Each consumer thread handles one payment at a time, and each payment makes **4 sequential round trips** (dedupe insert, account lock, one booking statement, commit). Throughput per thread is `1 / (4 × round-trip time)`. At +500 ms per round trip that is 0.5 payments/s per thread, 1.5/s for 3 processors, against 20/s offered. Before the booking statement was merged it was 8 round trips and 0.74/s.

## Triage
1. Confirm it is the database: processor spans in Tempo show JDBC client spans of hundreds of milliseconds each.
2. On PostgreSQL: `SELECT pid, state, wait_event_type, wait_event, now() - query_start AS age, left(query, 60) FROM pg_stat_activity WHERE datname = 'payflow' ORDER BY age DESC;`
3. Look for lock waits (`wait_event_type = 'Lock'`), long-running transactions, or I/O waits.
4. Check the network path if a proxy sits in between (in the lab: Toxiproxy `curl localhost:8474/proxies/postgres/toxics`).

## Mitigation
- Remove the cause (kill the blocking query, remove the toxic, fail over).
- Do **not** scale processors to "catch up" while the database is slow. Once it is healthy, the backlog drains on its own: 13,805 payments drained in about 10 seconds.

## Related
`pf-hikari-exhausted`, `pf-latency-fast-burn`, incident `inc-2026-11-20-db-latency`.
