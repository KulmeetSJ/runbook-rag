---
id: pf-prometheus-stale
title: Prometheus shows data from an earlier run
service: payflow
version: 1
updated: 2026-11-20
---
# Prometheus shows data from an earlier run

## Symptom
After `docker compose up -d --force-recreate prometheus`, graphs and burn-rate windows still contain spikes from an earlier experiment, so a 1-hour burn rate is already high before anything happens.

## Cause
The Prometheus image declares an anonymous volume for its data directory. Compose keeps anonymous volumes across `--force-recreate`.

## Fix
`docker compose rm -sfv prometheus && docker compose up -d prometheus` (`-v` removes the anonymous volume). Or `docker compose down -v` for the whole stack.

## Why it matters for alert tests
Burn-rate alerts depend on window history. A Prometheus with only 2 minutes of history makes the 1-hour window behave like a short window, so alert timings measured on a fresh stack look faster than they would be in production. For realistic time-to-page numbers, run at least one hour of healthy traffic first.
