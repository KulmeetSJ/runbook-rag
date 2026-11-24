---
id: inc-2026-11-20-db-latency
title: "Incident notes: slow database stalled payments"
service: payflow
version: 1
updated: 2026-11-24
---
# Incident notes 2026-11-20: slow database stalled payments (lab exercise)

Incident commander: Priya Raman (priya.raman@example.com, mobile +44 7700 900123).
Communications: Daniel Okafor (daniel.okafor@example.com).
Database on-call: Mei Lin Chen, reachable on 020 7946 0958 out of hours.

## Timeline (UTC)
- 11:30 +500 ms latency injected on every PostgreSQL response.
- 11:31 Committed rate falls from 20/s to 0.74/s; gateway still returns 202 at normal latency.
- 11:39 `PaymentLatencyBudgetFastBurn` pending, 9.4 minutes in. It would have taken ~51 minutes with a full hour of history.
- 11:52 Latency removed. Backlog of 13,359 drained in 58 s.

## Impact
Payments accepted but committed late. No payment lost: 23,267 accepted, 23,267 booked; ledger balanced.

## Root cause
The latency SLI divided by completed payments, so payments stuck in the backlog were not counted. Each payment also made 8 sequential database round trips, which multiplied the latency.

## Actions
1. SLI denominator changed to accepted payments (done 2026-11-24, re-measured: page in 11.3 minutes).
2. Booking merged into one statement, 4 round trips instead of 8 (done; throughput under the fault doubled to 1.5/s).
3. Add a "time since oldest unprocessed payment" alert (open).
