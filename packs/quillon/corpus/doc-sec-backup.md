---
title: Backup and disaster recovery
audience: public
owner_scope: everyone
authority: rule
version_chain: sec-backup
effective_from: '2026-07-01'
supersedes: null
links: []
type: security
doc_id: doc-sec-backup
---

# Backup and disaster recovery

## Purpose and scope

This document describes how Quillon protects customer contract data through backups and how we recover the Quillon service after a disruption. It applies to the contract-management platform, including drafting from templates, the clause library, approval workflows, e-signature, obligation tracking, renewal alerts and search across signed contracts. It is published for customers, prospective customers and their security reviewers.

## Recovery objectives

Our recovery objectives set the standard that the platform and the operations team are measured against during an incident.

The recovery point objective is 1 hour. In the event of a platform-wide data loss, we commit to restoring customer data to a state no more than one hour before the disruption began.

The recovery time objective is 4 hours. For a disruption that requires restoring the service from backups, we commit to bringing the affected services back to operation within four hours of the decision to invoke recovery.

These objectives describe targets for the service as a whole. Individual incidents may take longer to resolve when their cause or scope requires it, and we report any such delay to affected customers through our status communications.

## Backup coverage

Quillon backs up the data stores that hold customer contracts, drafts, templates, clause library content, approval records, signature evidence, obligation and renewal records, and the search indexes that support retrieval across signed contracts. Backups are taken on a continuous and scheduled basis so that the recovery point objective can be met.

Backups are encrypted before they are written to storage and are kept in a separate storage environment from the production systems they protect. Access to backup storage is limited to a small set of authorised operations staff, and access events are logged.

Backups are kept for 35 days. After that period, older backups are removed according to our data retention schedule, unless a customer agreement or a legal hold requires a different period.

## Restoration testing

Backups are only useful if they can be restored. The operations team tests restoration on a regular schedule, including sampled restores of customer-scope data into an isolated environment. Results are recorded, and any failed restore is treated as a defect and tracked to closure.

Recovery procedures are documented as runbooks. Each runbook names the systems involved, the order of restoration, the people responsible for each step and the checks that confirm the service is healthy before it is returned to customers.

## Roles during an incident

An incident commander coordinates the recovery and decides when to invoke the disaster recovery procedure. Engineering staff carry out the restoration steps defined in the runbooks. The security team confirms that restored systems have the expected access controls and that no unauthorised change has been introduced during the incident.

Customer communications are issued through our status channel and, where a contract requires it, directly to the customer's named contacts.

## Shared responsibilities

Customers retain responsibility for the accuracy of the contract data they enter, for the users they grant access to, and for any local copies they choose to keep. We recommend that customers who need an independent copy of their contract records export them on a schedule that suits their own compliance requirements.

## Review

This document is reviewed at least once a year and whenever the platform architecture, storage arrangements or recovery procedures change in a way that affects the commitments stated here. The version in force is the one published on our security page, effective from 2026-07-01.
