---
id: pf-rebalance
title: Processor instance died, partitions orphaned
service: payflow
version: 2
updated: 2026-11-21
---
# A processor instance died and its partitions are orphaned

The consumer group uses the **cooperative-sticky** assignor: when membership changes, only the moved partitions stop; the others keep consuming.

## Timing
- A crashed instance (SIGKILL, OOM) is only removed from the group when its heartbeats stop for `session.timeout.ms` (**45 s**). Its partitions get no consumer for that time and lag builds on them. Measured: partitions reassigned 46 s after the kill; lag peaked around 800 at 50 payments/s and recovered 71 s after the kill.
- A clean shutdown (`docker compose stop`) leaves the group immediately, so no gap.
- A restarted instance gets partitions back about 11 s after it starts (JVM start plus group join).

## Steps
1. `kafka-consumer-groups.sh --describe --group payment-processor`: look for partitions with no `CONSUMER-ID`.
2. Wait up to 45 s for the rebalance, or restart the dead instance.
3. Nothing is lost: offsets are committed only after the database transaction, so un-committed work is redelivered and the dedupe table absorbs any duplicates.

## Tuning
Lowering `session.timeout.ms` to 10 s shortens the gap but makes long GC pauses look like deaths and cause needless rebalances.
