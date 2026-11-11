---
title: Subprocessors
audience: public
owner_scope: everyone
authority: rule
version_chain: sec-subprocessors
effective_from: '2026-07-01'
supersedes: null
links:
- doc-clause-dpa
type: security
doc_id: doc-sec-subprocessors
---

# Subprocessors

## Purpose

This document lists the third-party subprocessors that Quillon uses to deliver its contract-management service to law firms and corporate finance teams. It is published by the Quillon security team and applies to all customers from the effective date shown below.

## Document details

- Document type: Security
- Audience: Public
- Authority: Rule
- Effective from: 2026-07-01

## Scope

A subprocessor is a third party that processes customer data on Quillon's behalf in order to provide part of the service. This document covers the service functions that depend on subprocessors, including drafting from templates, clause library, approvals, e-signature, obligation tracking, renewal alerts and search across signed contracts.

Quillon does not list internal teams or staff as subprocessors. Where a function is performed entirely by Quillon, it is not included here.

## Subprocessor list

The table below sets out each subprocessor, the function it performs for Quillon, and the relevant service area.

| Subprocessor | Function | Service area |
|---|---|---|
| Cumulus Cloud | Hosts Quillon workloads in the US and EU | Platform infrastructure |
| Dispatchly | Sends Quillon's transactional email | Notifications and renewal alerts |
| Verbis AI | Provides the model behind AI clause review | Clause review |
| Ledgerpay | Processes card payments | Billing |
| Signet Trust | Provides trusted timestamps for e-signature | E-signature |

## How subprocessors are used

Each subprocessor receives only the data needed for its stated function. Quillon does not permit subprocessors to use customer contract content for their own purposes, including model training, unless a customer has given separate written consent.

Cumulus Cloud hosts Quillon workloads in the US and EU, which allows Quillon to keep customer data within the regions described in the service agreement. Dispatchly sends transactional email, such as approval requests and renewal alerts. Verbis AI provides the model behind AI clause review, and clause review requests are limited to the content needed for that review. Ledgerpay processes card payments, and Quillon does not store full card numbers. Signet Trust provides trusted timestamps for e-signature, which record the time at which a signature event occurred.

## Changes to subprocessors

Quillon will update this page before a new subprocessor begins processing customer data. Customers who subscribe to notifications receive a message when the list changes. Customers may raise objections to a new subprocessor through their account contact, and Quillon will respond in line with the terms of the service agreement.

## Contractual safeguards

Each subprocessor is bound by written terms that require confidentiality, appropriate security measures and deletion or return of data at the end of its function. Quillon reviews subprocessor security posture as part of its supplier governance process.

## Questions

Questions about this list or about a specific subprocessor should be sent to the Quillon security team through the support channel listed in the customer portal.
