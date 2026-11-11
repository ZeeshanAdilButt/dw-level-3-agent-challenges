---
title: Data residency
audience: public
owner_scope: everyone
authority: rule
version_chain: sec-residency
effective_from: '2026-07-01'
supersedes: null
links:
- doc-sup-region-change
type: security
doc_id: doc-sec-residency
---

# Data residency

## Purpose

This document describes where Quillon stores customer data, how a data region is selected, and how backups are handled. It applies to all Quillon workspaces that hold contract content, metadata, signature records, and obligation and renewal data. It is issued by the Quillon security team and takes effect on 2026-07-01.

## Scope

Data residency covers the primary storage of workspace content, including drafts, executed contracts, clause library entries, approval records, e-signature evidence, obligation records, and search indexes derived from signed contracts. It also covers backups of that content. It does not describe where Quillon's corporate systems, support tooling, or billing records are stored, which are governed by separate documents.

## Available regions

Quillon currently offers two data regions. Each workspace is assigned to one region only.

| Region | Workspace hosting location | Region identifier used in administration |
|---|---|---|
| US | Virginia | US |
| EU | Frankfurt | EU |

Customers who need a region not listed above should contact their Quillon account representative before the workspace is created. No other hosting locations are offered for customer workspaces.

## Choosing a region

The data region is chosen when the workspace is created. Workspace administrators cannot select or change the region afterwards through the product interface. A workspace that was created in one region remains in that region for its full life. Customers who need a different region must create a new workspace and migrate content through a supported export and import process, which is subject to the terms in the customer agreement.

Because the choice is fixed at creation, the customer's legal and compliance team should confirm the intended region before the workspace is provisioned.

## Backups

Backups stay in the same region as the workspace. A backup of a US workspace is stored only in Virginia, and a backup of an EU workspace is stored only in Frankfurt. Quillon does not copy workspace backups to the other region or to any other location for disaster recovery purposes.

Backup encryption, retention periods, and restore procedures are described in the separate backup and recovery standard. The residency commitment in this document applies to where backup data is stored, regardless of those settings.

## Data in transit

Traffic between customer browsers, integrations, and Quillon services is encrypted in transit. Requests from a workspace are processed in the region that hosts the workspace. Where a feature requires a service outside the workspace region, the request is handled in a way that keeps customer content within that region, and the feature documentation identifies any exceptions. Customers should review that documentation before enabling optional integrations.

## Subprocessors and support access

Access to customer content by Quillon staff is limited to named support and operations roles, requires an approved access request, and is logged. Staff access from outside the workspace region does not move stored data out of its region. Subprocessors that may process customer content are listed in the subprocessor register, which states the region each subprocessor operates in.

## Responsibilities

The Quillon security team maintains the hosting configuration for each region, reviews backup placement during routine audits, and reports any deviation from this document to the customer's account representative. Workspace administrators are responsible for selecting the correct region at creation and for ensuring that their own exports and integrations do not send content to locations their policies prohibit.

## Exceptions and changes

Any exception to this document must be approved in writing by the head of security and recorded with the affected customer. Changes to available regions or hosting locations will be announced in advance through the customer notification process, and this document will be reissued with a new effective date. Customers with questions about residency should raise them with their account representative.
