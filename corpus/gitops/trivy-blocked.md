---
id: gitops-trivy-blocked
title: CI failed on Trivy image scan
service: gitops
version: 1
updated: 2026-11-19
---
# CI failed: Trivy found HIGH or CRITICAL vulnerabilities

The build job scans the image with Trivy and fails on HIGH or CRITICAL findings that have a fix available (`--ignore-unfixed`). An SBOM (Syft, SPDX JSON) is attached to every build.

## Steps
1. Read the Trivy table in the job log: package, installed version, fixed version.
2. OS package in the base image → bump the base image (for example a newer `eclipse-temurin:21-jre` patch tag) and rebuild.
3. Java dependency → bump it in `pom.xml`, or override a transitive version in `dependencyManagement`.
4. No fix possible and the vulnerable code is not reachable → add a `.trivyignore` entry with the CVE, a reason and an expiry date, reviewed in the PR.

## Do not
Remove the scan step or raise the threshold to get a release out. Use the time-boxed ignore instead, so the exception is visible.
