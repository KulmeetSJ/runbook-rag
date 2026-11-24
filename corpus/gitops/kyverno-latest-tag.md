---
id: gitops-kyverno-latest
title: Kyverno rejected a deployment (latest tag)
service: gitops
version: 1
updated: 2026-11-19
---
# Kyverno rejected the manifest: disallow-latest-tag

## Message
`validation error: Using a mutable image tag e.g. 'latest' is not allowed. rule require-image-tag failed`

## Why the policy exists
`:latest` (or no tag) makes deploys non-reproducible: the same manifest can run different code tomorrow, and rollbacks cannot return to a known image.

## Fix
Use the immutable tag CI produces (the Git SHA), for example `ghcr.io/<owner>/demo-app:3f2c1ab`. Better, pin the digest: `demo-app@sha256:...`.

## Exception process
None for prod. For a throwaway namespace, a `PolicyException` resource scoped to that namespace, reviewed in a PR.
