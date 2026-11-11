---
title: Vulnerability disclosure
audience: public
owner_scope: everyone
authority: rule
version_chain: sec-vdp
effective_from: '2026-07-01'
supersedes: null
links: []
type: security
doc_id: doc-sec-vdp
---

# Vulnerability disclosure

## Purpose

This policy describes how security researchers and other outside parties can report suspected security vulnerabilities in Quillon's contract-management software and related services. Quillon provides drafting from templates, a clause library, approvals, e-signature, obligation tracking, renewal alerts, and search across signed contracts to law firms and corporate finance teams. This document applies from 2026-07-01 and is the authoritative statement of how we receive and handle vulnerability reports.

## Scope

This policy covers the Quillon web application, its public application programming interfaces, and the e-signature and document-handling components that our customers use to manage their agreements. Reports about infrastructure or third-party services that we do not operate may be redirected to the responsible party.

The following are out of scope: denial-of-service testing, social engineering of Quillon staff or customers, physical attacks against offices or data centers, and testing that accesses data belonging to customers other than the researcher's own test accounts. Researchers must not retain, copy, or disclose customer contract content encountered during testing.

## How to report

Send reports to the security disclosure inbox published on the Quillon security page. Include a clear description of the issue, the affected component or endpoint, steps to reproduce, the potential impact as you understand it, and any proof-of-concept material needed to verify the finding. Encrypted submissions are welcome. Please do not include live customer data in your report; a redacted or synthetic example is sufficient.

## Our response

Reports to the security disclosure inbox are acknowledged within 2 business days. The acknowledgment confirms receipt and assigns a tracking reference. Our security team then triages the report, assesses severity, and contacts the reporter with questions or a preliminary assessment. We will keep the reporter informed of material progress and will tell the reporter when the issue is resolved, unless the reporter asks us not to.

Severity is assessed on the potential impact to customer data and service availability, the difficulty of exploitation, and whether the issue is already known or being exploited. Remediation timing follows that assessment, with the most serious issues prioritized for immediate action.

## Coordinated disclosure

We ask researchers to give us a reasonable period to investigate and fix a confirmed issue before any public disclosure. We will work with the reporter on a timeline and will credit the reporter in release notes or on the security page if the reporter wishes to be named. We do not offer monetary rewards under this policy.

## Safe harbor

Quillon will not initiate or support legal action against researchers who act in good faith, follow this policy, avoid privacy violations and service disruption, and report findings promptly. This statement does not authorize activity that breaks applicable law, and it does not extend to third parties.

## Summary of key commitments

| Item | Commitment |
|---|---|
| Acknowledgment of reports to the disclosure inbox | Within 2 business days |
| Contact channel | Security disclosure inbox on the Quillon security page |
| Customer contract content | Must not be accessed, retained, or disclosed |
| Monetary rewards | Not offered under this policy |

## Review

The security team reviews this policy at least once a year and whenever the scope of our products changes materially. Questions about this policy should be sent to the security disclosure inbox.
