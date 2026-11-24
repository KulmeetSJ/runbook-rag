---
id: misc-postmortem-template
title: Postmortem template
service: all
version: 1
updated: 2026-11-20
---
# Postmortem template (blameless)

1. **Summary**: two or three sentences: what broke, for how long, impact in SLO terms.
2. **Impact**: payments affected, budget consumed, customer-visible symptoms.
3. **Timeline**: UTC timestamps, from first signal to full recovery, including when humans were paged.
4. **Detection**: how we found out and how long it took. Was the alert fast enough?
5. **Root cause and contributing factors**: systems and decisions, not people.
6. **What went well / what went wrong**.
7. **Action items**: each with an owner and a due date, labelled prevent, detect or mitigate. At least one must be completed and verified before the postmortem is closed.
