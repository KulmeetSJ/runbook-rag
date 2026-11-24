---
id: gitops-sealed-secrets
title: Sealed Secrets cannot decrypt after cluster rebuild
service: gitops
version: 1
updated: 2026-11-19
---
# Sealed Secrets: "no key could decrypt secret"

## Cause
The cluster was rebuilt and the Sealed Secrets controller generated a **new** key pair. SealedSecrets in Git were encrypted with the old public key, so the new controller cannot decrypt them.

## Fix: restore the backed-up key
1. The key is backed up outside the cluster when it is created (a Kubernetes Secret with label `sealedsecrets.bitnami.com/sealed-secrets-key`), in a location only the platform owner can read. Never in Git.
2. `kubectl apply -f <backup>.yaml -n kube-system`
3. `kubectl rollout restart deployment sealed-secrets-controller -n kube-system`
4. Check: `kubectl get secret -n <env>` shows the decrypted secrets; Argo CD resyncs.

## If the backup is lost
Re-seal every secret with the new public key (`kubeseal --fetch-cert`) from the original plaintext values. This is why the backup is part of cluster setup (`make up`).
