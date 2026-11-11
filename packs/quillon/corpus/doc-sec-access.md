---
title: Staff access to customer data
audience: public
owner_scope: everyone
authority: rule
version_chain: sec-access
effective_from: '2026-07-01'
supersedes: null
links: []
type: security
doc_id: doc-sec-access
---

# Staff access to customer data

## Purpose

This document sets out how Quillon staff may access customer data held in the Quillon contract-management platform, and how that access is logged, reviewed and removed. It applies to all employees, contractors and service providers who work on or support the platform. Customer data includes uploaded contracts, drafts, clause library entries that a customer has created, approval records, signature records, obligation and renewal entries, and search indexes built from a customer's signed agreements.

## Scope

The rules below cover access to production systems, support tooling, backups, logs and analytics environments that contain customer data. They do not cover data that Quillon holds about its own staff for employment purposes, which is governed by separate policies.

## Principles of access

Access to customer data follows three principles. First, access is granted only where a documented business need exists, such as resolving a support request a customer has raised or investigating a reported fault. Second, access is limited to the minimum scope and duration needed for the task. Third, no staff member may use access granted for one purpose to view data for another purpose.

Customer data is not used for product development, marketing or sales activity unless the customer has given written consent for that specific use. Aggregated, de-identified operational metrics, such as counts of documents processed or average approval times, may be used for service monitoring.

## Granting and removing access

Access requests are raised through the internal access workflow and must name the requester, the customer account concerned, the reason and the requested duration. A manager and, for production data, a member of the security team must approve each request. Standing access to production customer data is not granted as a default role. Where an engineer requires recurring access, it is provided through a time-limited elevated role that expires automatically.

Access is removed when a staff member changes role or leaves Quillon, and access tokens and credentials are revoked on the same working day as the change. Accounts that have been inactive for an extended period are disabled automatically.

## Logging of access

Every access to customer data by Quillon staff is logged. Each log entry records the identity of the staff member, the customer account, the system or data set accessed, the time of access and the reason recorded in the access workflow. Logs are stored in a central location that staff with production access cannot alter or delete.

Logged access events are reviewed quarterly by the security team. The review compares access events against approved requests, checks for access outside working patterns or without a linked support or engineering ticket, and confirms that elevated roles have expired as scheduled. Staff access to customer data is logged and reviewed every quarter, and the review results are recorded and retained for audit purposes.

## Review outcomes

Where a review identifies access without an approved reason, the security team investigates and records the findings. Confirmed misuse is treated as a serious disciplinary matter and may result in dismissal and referral to the relevant authorities. Where the review identifies a control gap, such as an expired role that was not removed, the owning team must correct it and the security team verifies the fix.

## Customer visibility

Customers may request a report of Quillon staff access to their account data through their account administrator. Reports list access events in the same fields described above. Requests are handled through the standard support channel.

## Responsibilities

The security team owns this policy, maintains the access workflow and runs the quarterly review. Engineering and support managers are responsible for ensuring their teams request access correctly and for approving requests within their remit. All staff must complete access-handling training before receiving any access to customer data and must report suspected misuse immediately.

## Review of this document

This document takes effect on 2026-07-01 and replaces any earlier version covering staff access to customer data. The security team reviews it at least once each year, and sooner if a material change to systems, legal obligations or customer commitments requires it.
