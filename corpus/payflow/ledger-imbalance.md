---
id: pf-ledger-imbalance
title: Ledger or balance reconciliation failed
service: payflow
version: 1
updated: 2026-11-21
---
# Ledger or balance reconciliation failed

Invariants that must always hold:
- `SUM(amount) FILTER (WHERE direction='DEBIT')` = `SUM(amount) FILTER (WHERE direction='CREDIT')` over `ledger_entries`.
- `SUM(balance)` over `accounts` equals the seeded total (100,000,000.00 in the lab).
- Every accepted payment (HTTP 202) has exactly one row in `payments`.

## If an invariant fails
1. **Stop**: this is a severity-1 correctness incident, not a performance one. Page the payments owner.
2. Freeze replays and manual fixes so the evidence is not changed.
3. Find the first bad payment: compare per-payment debit and credit sums, `SELECT payment_id FROM ledger_entries GROUP BY payment_id HAVING sum(CASE direction WHEN 'DEBIT' THEN amount ELSE -amount END) <> 0;`
4. The booking runs as one transaction (payment row, both ledger entries, both balance updates in one statement, and the code checks exactly 2 balance rows were updated). A partial booking points at a manual change or a migration, not normal processing.

In every chaos test so far (broker kill, consumer kill, +500 ms database latency) the invariants held.
