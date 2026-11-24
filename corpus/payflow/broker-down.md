---
id: pf-broker-down
title: Kafka broker down, under-replicated partitions
service: payflow
version: 2
updated: 2026-11-21
---
# Kafka broker down / under-replicated partitions

Cluster: 3 brokers in KRaft combined mode (each broker is also a controller), replication factor 3, `min.insync.replicas=2`, producers use `acks=all`.

## What to expect when one broker dies
- Leaders for its partitions move to the other brokers. After a SIGKILL this takes about **10 seconds**: the controller only notices when heartbeats stop (`broker.session.timeout.ms`, 9 s). A clean `docker stop` hands leadership over immediately.
- During those seconds, sends to the affected partitions wait. If they wait longer than the gateway's `delivery.timeout.ms` (10 s), the gateway returns **503** instead of 202. That is correct: nothing is acknowledged unless it is durable. See `pf-gateway-503`.
- With 2 of 3 brokers up, `min.insync.replicas=2` is still met, so writes continue. With 1 of 3 up, every `acks=all` send fails.

## Steps
1. `docker compose ps kafka-1 kafka-2 kafka-3` to see which broker is down.
2. Restart it: `docker compose start kafka-2`. It rejoins every ISR within a few seconds.
3. Check under-replicated partitions are 0: `kafka-topics.sh --bootstrap-server kafka-1:9092 --describe --under-replicated-partitions`.
4. Leadership moves back to the preferred leader within ~5 minutes (`auto.leader.rebalance.enable`). No action needed.

## Data loss check
Run the reconcile query: every 202 must have exactly one payment row. In the chaos test (broker SIGKILL, 64 s down) 0 of 11,631 payments were lost.
