---
id: pf-alertmanager-routing
title: Alert firing in Prometheus but not delivered
service: payflow
version: 1
updated: 2026-11-21
---
# Alert is firing in Prometheus but nobody was notified

## Checks
1. Prometheus UI → Alerts: is it `firing` or only `pending`? Alerts with a `for:` clause stay pending first (2 minutes for the fast-burn pages).
2. Alertmanager: `curl -s localhost:9093/api/v2/alerts | jq '.[].labels.alertname'`. If it is missing, check Prometheus' `alerting.alertmanagers` target.
3. Routing: alerts with `severity: page` go to the `page` receiver; `severity: ticket` to `ticket`. A typo in the label (for example `sev: page`) falls through to the default receiver.
4. Silences: `curl -s localhost:9093/api/v2/silences | jq '.[] | select(.status.state=="active")'`. An old silence matching `alertname=~".*Burn"` hides every burn alert.
5. Inhibition: a firing page inhibits the matching ticket by design.

## Test routing safely
`amtool alert add test_alert severity=ticket --alertmanager.url=http://localhost:9093` and check which receiver gets it.
