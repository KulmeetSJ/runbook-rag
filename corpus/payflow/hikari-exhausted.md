---
id: pf-hikari-exhausted
title: Connection pool exhausted (Connection is not available)
service: payflow
version: 1
updated: 2026-11-21
---
# HikariCP: "Connection is not available, request timed out"

## Meaning
A processor thread waited `connectionTimeout` (default 30 s) for a pooled connection and gave up. The pool size is 10 per processor instance. PostgreSQL `max_connections` is 100, so at most about 9 processor instances can each hold a full pool, with headroom for admin sessions.

## Common causes
1. Slow queries holding connections longer (see `pf-db-latency`). The pool is a symptom, not the cause.
2. A connection leak: a code path that opens a transaction and never returns. Check `hikaricp_connections_active` stays at the maximum while `hikaricp_connections_pending` climbs, even at low load.
3. Too many instances for `max_connections`: PostgreSQL logs `FATAL: sorry, too many clients already`.

## Steps
1. Grafana → processor dashboard → Hikari panel: active, idle, pending.
2. On PostgreSQL: `SELECT count(*), state FROM pg_stat_activity WHERE datname = 'payflow' GROUP BY state;`. Many `idle in transaction` sessions = leak or stuck transactions.
3. If it is a leak, restart the affected instance (connections are released) and file a bug.

## Do not
Raising the pool size past what PostgreSQL can serve moves the queue from the pool into the database.
