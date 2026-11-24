---
id: pf-latency-fast-burn
title: PaymentLatencyBudgetFastBurn page
service: payflow
version: 3
updated: 2026-11-24
---
# PaymentLatencyBudgetFastBurn (page)

SLO: 99% of **accepted** payments committed within 2 s of acceptance, over 28 days. Error budget: 1%.

## Alert logic
Fires when the error ratio is above 14.4 × 1% = 14.4% over **both** 1 hour and 5 minutes, for 2 minutes. At a 14.4x burn the whole 28-day budget would be gone in about 2 days.

## SLI definition (changed 2026-11-24)
`1 - committed_within_2s / accepted`. The denominator is `payments_accepted_total` from the gateway. It used to be completed payments, which hid stalls: a stuck payment was not counted at all until it finally completed, so a processing stall took about 51 minutes to page. See incident `inc-2026-11-20-db-latency`.

## First five minutes
1. Is it a stall or a slowdown? Compare accepted vs committed rates (see `pf-lag-growing`).
2. All partitions or one? All → shared dependency (`pf-db-latency`). One → `pf-poison-message`.
3. Was there a deploy in the last 15 minutes? Cold JVMs right after a deploy can breach the SLO at rates the warm system handles (`pf-cold-start`).
4. Is the success SLO also burning? Then failures are being retried, and retries add latency (`pf-dlt-growth`).

## Resolution
The page clears once the 5-minute window recovers, usually 4–5 minutes after the fix. The slow-burn ticket may stay open longer because its 30-minute window still contains the incident.
