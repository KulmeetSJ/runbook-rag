---
id: pf-traces-missing
title: Traces missing in Grafana Tempo
service: payflow
version: 1
updated: 2026-11-20
---
# Traces are missing in Tempo

The services use the OpenTelemetry Java agent, which sends OTLP to the OpenTelemetry Collector, which exports to Tempo (traces) and Loki (logs).

## Checks, in order
1. Is the agent loaded? The service log starts with `opentelemetry-javaagent - version: ...`. If not, the agent jar was not readable: files added with Docker `ADD` are mode 600, and `--chmod` also changes the directory it creates, so copy the jar into an existing directory such as `/app`.
2. Is the collector healthy? `docker compose logs otel-collector | tail`. Collector 0.164 renamed the exporters: use `otlp_grpc` and `otlp_http`. An old `otlp` exporter name makes the collector fail at startup.
3. Is `OTEL_EXPORTER_OTLP_ENDPOINT` pointing at the collector service name, not `localhost`?
4. In Grafana Explore, search Tempo by service name `payment-gateway` for the last 15 minutes.

## Trace shape to expect
One trace spans gateway → Kafka → processor → PostgreSQL. The Kafka hop is linked through trace context in message headers.
