---
id: gitops-kind-cluster
title: Local kind cluster not starting
service: gitops
version: 1
updated: 2026-11-20
---
# Local kind cluster "gitops-demo" will not start

## Checks
1. Docker Desktop is running and has at least 6 GB memory assigned.
2. `kind get clusters` lists `gitops-demo`. If not, `make up` recreates it (and restores the Sealed Secrets key; see `gitops-sealed-secrets`).
3. Port conflict: the ingress maps host ports 80/443. Another container or process on those ports makes the node container fail to start.
4. The node container used to be created with `restart=always`, so it started with Docker and consumed memory while other projects ran. It is now `restart=no`: start it explicitly with `docker start gitops-demo-control-plane`.
