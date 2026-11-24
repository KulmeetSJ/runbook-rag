---
id: pf-lag-growing
title: Consumer lag growing on payments.initiated
service: payflow
version: 3
updated: 2026-11-21
---
# Consumer lag growing on payments.initiated

Alert: `PaymentConsumerLagGrowing` (ticket). Source: kafka-exporter, `kafka_consumergroup_lag{consumergroup="payment-processor"}`.

## What it means
The processors are committing fewer payments per second than the gateway accepts. Lag alone is not an SLI: a small, stable lag is normal at high load. What matters is whether lag keeps **growing** and whether the latency SLO is burning.

## Triage
1. Compare rates in Prometheus: `sum(rate(payments_accepted_total[1m]))` (gateway) vs `sum(rate(payments_processed_total{outcome!="duplicate"}[1m]))` (processors). A gap of more than 5% for 5 minutes means the consumers are behind.
2. Check lag per partition. Lag on **one** partition points at a slow or poison message on that partition (see `pf-poison-message`). Lag on **all** partitions points at a shared dependency, usually PostgreSQL (see `pf-db-latency`).
3. Check consumer group membership: `kafka-consumer-groups.sh --bootstrap-server kafka-1:9092 --describe --group payment-processor`. Partitions with no owner mean a consumer died and the group has not rebalanced yet (see `pf-rebalance`).
4. Check the processor logs for `Connection is not available` (Hikari pool exhausted) or retry-topic hops.

## Mitigation
- If one consumer thread per instance is the bottleneck and there are fewer than 6 consumers, scale processors: `docker compose up -d --scale payment-processor=6`. More than 6 consumers does nothing: there are 6 partitions and the 7th consumer sits idle.
- If the database is slow, scaling processors makes it worse (more connections, same slow queries). Fix the database first.

## Recovery check
Lag returns to under 25 and the burn rate on `slo:payment_latency:error_ratio_rate5m` drops below 1x.
