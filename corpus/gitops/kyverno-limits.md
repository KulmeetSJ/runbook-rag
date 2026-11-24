---
id: gitops-kyverno-limits
title: Kyverno rejected a pod (missing resource limits)
service: gitops
version: 1
updated: 2026-11-19
---
# Kyverno rejected the pod: require-requests-limits

## Message
`validation error: CPU and memory resource requests and memory limits are required. rule validate-resources failed`

## Fix
Set in the Helm values for every container, including sidecars and init containers:
```yaml
resources:
  requests: { cpu: 100m, memory: 256Mi }
  limits: { memory: 512Mi }
```
A CPU **limit** is deliberately not required: CPU limits cause throttling under bursts, while a memory limit protects the node.

## Related policies
- `disallow-privileged-containers`: `privileged: true` is rejected.
- `gitops-kyverno-latest` for image tags.
