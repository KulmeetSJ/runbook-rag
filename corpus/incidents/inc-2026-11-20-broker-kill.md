---
id: inc-2026-11-20-broker-kill
title: "Incident notes: broker killed, 72 payments refused"
service: payflow
version: 1
updated: 2026-11-21
---
# Incident notes 2026-11-20: one Kafka broker killed (lab exercise)

On-call: Tomás Herrera (tomas.herrera@example.com, +1 415 555 0142). Shadow: Aisha Khan.

## What happened
kafka-2 was killed with SIGKILL at 50 payments/s and restarted after 64 s.
- Its partitions had no leader for 10.0 s (the controller waits `broker.session.timeout.ms`).
- 72 requests got HTTP 503 because the gateway's `delivery.timeout.ms` (10 s) expired. They were not acknowledged, so the clients knew to retry.
- Worst 30-second gateway p99: 9.8 s.
- kafka-2 was back in every in-sync replica set 5 s after it restarted.

## Impact
0 of 11,631 accepted payments lost. 72 refused (503). Money conserved.

## Follow-up
Consider raising `delivery.timeout.ms` above the failover time, trading longer client waits for fewer 503s.
