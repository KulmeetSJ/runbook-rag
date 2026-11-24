---
id: pf-latency-slow-burn
title: PaymentLatencyBudgetSlowBurn ticket
service: payflow
version: 1
updated: 2026-11-20
---
# PaymentLatencyBudgetSlowBurn (ticket)

Fires when the latency error ratio is above 6% over both 6 hours and 30 minutes. At a 6x burn the 28-day budget lasts about 5 days.

This is a ticket, not a page: handle it in working hours. It usually means one of:
- a recent incident is still inside the 30-minute window (it clears on its own);
- a steady, low-grade slowdown, for example load creeping up towards the knee (750–1,000 payments/s with 3 processors on the lab laptop);
- retries: a dependency failing a small share of attempts adds 0.5–4 s to those payments.

## Steps
1. Check whether the fast-burn page fired recently. If yes, link the ticket to that incident and wait for the window to pass.
2. If not, look at the e2e latency histogram by hour. A slow climb with load means capacity; plan scaling.
3. Check `error_budget_remaining`. Under the error budget policy, if less than 25% is left, freeze risky deploys until it recovers.
