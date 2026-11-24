---
id: pf-processor-oom
title: Processor container restarting (OOM)
service: payflow
version: 1
updated: 2026-11-21
---
# Processor container keeps restarting (out of memory)

The processors run with `-XX:MaxRAMPercentage=60 -XX:+ExitOnOutOfMemoryError` in a 512 MB container. On an `OutOfMemoryError` the JVM exits at once instead of limping on, Docker restarts it, and the consumer group rebalances.

## Symptoms
- `docker compose ps` shows restarts; logs end with `Terminating due to java.lang.OutOfMemoryError`.
- Exit code 137 instead means the kernel OOM-killer acted: the container limit was hit before the heap limit (too much off-heap memory, for example the OpenTelemetry agent plus metaspace).

## Steps
1. `docker inspect --format '{{.State.ExitCode}} {{.State.OOMKilled}}' <container>`
2. Heap OOM: check for unbounded in-memory collections. A large `max.poll.records` with big messages is the usual suspect.
3. Container OOM-kill: lower `MaxRAMPercentage` to 50, or raise the container limit.
4. Each restart costs a rebalance; see `pf-rebalance` for timing.
