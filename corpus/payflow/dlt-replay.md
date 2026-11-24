---
id: pf-dlt-replay
title: Replaying messages from the DLT
service: payflow
version: 2
updated: 2026-11-20
---
# Replaying messages from the dead-letter topic

Replay is safe to repeat: the processor is idempotent. Each event ID is inserted into `processed_events` in the same transaction as the ledger write, so a second replay of the same event is detected and skipped (`outcome="duplicate"`).

## Steps
1. Confirm the root cause is fixed (see `pf-dlt-growth`).
2. Dry run: `curl -s 'localhost:8081/admin/dlt?limit=100' | jq length` to see how many records will be replayed.
3. Replay one record first: `curl -X POST localhost:8081/admin/dlt/replay/<partition>/<offset>`.
4. Check the payment row: `SELECT status, delivery_attempt FROM payments WHERE payment_id = '<eventId>';`
5. Replay the rest: `curl -X POST 'localhost:8081/admin/dlt/replay?all=true'`.
6. Watch `payments_processed_total{outcome="duplicate"}`. A jump is expected if some records were already booked by an earlier replay.

## Do not
- Do not replay poison messages (`kind="poison"`). They will fail validation again and go straight back to the DLT.
- Do not delete the DLT topic to "clear" the alert. The records are the audit trail.
