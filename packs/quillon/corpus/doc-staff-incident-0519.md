---
title: 'Incident review: 19 May 2026 outage'
audience: internal
owner_scope: staff
authority: guide
version_chain: staff-incident-0519
effective_from: '2026-08-01'
supersedes: null
links: []
type: internal-notes
doc_id: doc-staff-incident-0519
---

# Incident review: 19 May 2026 outage

## Purpose and scope

This review records what happened during the outage on 19 May 2026, how the team responded, and what we will change. It is for staff only and must not be shared with customers. Customer-facing communication about the incident was handled separately by the support and account teams. This document covers the timeline and the cause, and it sets out the follow-up actions owners have agreed to.

## Summary

The 19 May 2026 outage lasted 74 minutes and affected users trying to sign in, open stored agreements, and start approval workflows. Once service was restored, we reviewed each affected account and issued service credits to 6 customers under the standard credit policy. The root cause was an expired internal certificate used for service-to-service authentication. The certificate had passed its renewal date without triggering any alert, so the failure appeared with no warning.

## Timeline

Early in the morning, the internal certificate reached its expiry time. Services that relied on it began rejecting requests from one another within minutes. Automated health checks detected elevated error rates, but the alerts were routed to a channel that had been muted during a planned maintenance window the previous evening, so the on-call engineer was not paged immediately.

The first customer reports arrived through the support queue. The support lead escalated to engineering, and the on-call engineer was paged. Engineers initially suspected a recent deployment and spent part of the incident rolling back a release that was not the cause. Once the failing authentication path was identified, the team located the expired certificate, issued a replacement, and restarted the affected services in a staged order. Service recovered after 74 minutes, and the status page was updated throughout.

## Cause

The certificate was issued with a fixed validity period and was not included in our renewal tracking. Renewal depended on a manual reminder that had been moved to a shared calendar during a team reorganisation and was never reattached to the owning team. No monitoring checked certificate expiry dates ahead of time. When the certificate expired, the failure was sudden and affected several services at once, because they all depended on the same credential.

## Contributing factors

Alert routing during planned maintenance suppressed the first signal. The rollback attempt consumed time that could have gone to direct diagnosis. Dependencies on a single shared credential meant that one expiry affected multiple product areas at the same time.

## Actions

The following actions have been agreed. Each has a named owner in the engineering operations group.

We will add automated monitoring for all internal certificates, with alerts at fixed intervals before expiry. Ownership of every certificate will be recorded in the service catalogue so that renewal responsibility cannot be lost in a reorganisation. Alert routing during maintenance windows will be changed so that critical health signals are never fully muted. The on-call runbook will be updated with a step that checks recent credential changes before any rollback is attempted. Finally, we will review which services share a credential and split those dependencies where practical.

## Status

The replacement certificate is in place, the monitoring change is scheduled for completion before the effective date of this guide, and the remaining actions are tracked in the engineering operations backlog. Staff with questions about this review should contact the engineering operations lead.
