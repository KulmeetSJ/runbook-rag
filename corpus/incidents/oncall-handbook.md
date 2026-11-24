---
id: misc-oncall-handbook
title: On-call handbook and escalation
service: all
version: 4
updated: 2026-11-22
---
# On-call handbook

## Rotation
Primary and secondary on-call rotate weekly on Monday 10:00 UTC. Handover is a 15-minute call covering open incidents, silences and error budgets.

## Escalation contacts (synthetic)
| Area | Owner | Contact |
|---|---|---|
| Payments platform | Priya Raman | priya.raman@example.com, +44 7700 900123 |
| Kafka | Tomás Herrera | tomas.herrera@example.com, +1 415 555 0142 |
| PostgreSQL | Mei Lin Chen | meilin.chen@example.com, 020 7946 0958 |
| Kubernetes / GitOps | Sam Whitfield | sam.whitfield@example.com |
| Cloud IAM | Aisha Khan | aisha.khan@example.com, +44 7700 900789 |

## Severity
- **SEV1**: money incorrect or payments lost (`pf-ledger-imbalance`), or all payments failing. Page the payments owner and open an incident channel.
- **SEV2**: SLO fast burn (page). Primary on-call leads.
- **SEV3**: tickets (slow burn, drift, lag growing).

## Rules
- Acknowledge pages within 5 minutes.
- Write the timeline as you go; the postmortem is blameless and due within 5 working days for SEV1/SEV2.
- Never share credentials or customer data in incident channels.
