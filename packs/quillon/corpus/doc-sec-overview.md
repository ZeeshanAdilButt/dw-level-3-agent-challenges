---
title: Security overview
audience: public
owner_scope: everyone
authority: rule
version_chain: sec-overview
effective_from: '2026-07-01'
supersedes: null
links:
- doc-sec-soc2
- doc-sec-encryption
type: security
doc_id: doc-sec-overview
---

# Security overview

## Purpose and scope

This document describes how Quillon protects the contract data that customers store, draft, approve, sign, and track within our contract-management platform. Quillon sells contract-management software as a service to law firms and corporate finance teams. The platform covers drafting from templates, a clause library, approval workflows, electronic signature, obligation tracking, renewal alerts, and search across signed contracts. Because contracts often contain commercially sensitive terms and personal information, we treat confidentiality, integrity, and availability as core product requirements rather than optional features.

This overview is written for customers, prospective customers, and their security reviewers. It describes controls at a general level. It does not reproduce internal architecture diagrams, configuration details, or incident-response playbooks, which we share under a non-disclosure agreement when a customer's review requires them.

## Governance and responsibilities

Security responsibilities at Quillon are assigned to a dedicated security team that reports to the engineering leadership group. The security team sets baseline requirements for code review, access control, vulnerability management, and vendor selection. Product teams own the implementation of those requirements within their services, and the security team reviews designs that touch customer data before release.

Every employee completes security awareness training when they join and again on a recurring schedule. Engineers receive additional training on secure coding practices relevant to the languages and frameworks they use. Staff who handle customer support or account administration receive guidance on identity verification and on recognizing social engineering attempts.

Customers who use Quillon remain responsible for how their own users are managed, including the assignment of roles, the removal of departing staff, and the configuration of approval chains that match their internal policies. Quillon provides the controls to support these responsibilities, and the account administrator guides described in our help materials explain how to use them.

## Certifications and independent assurance

Quillon holds ISO 27001 certification for the information security management system that covers the design, development, operation, and support of the contract-management platform. The certification is maintained through periodic surveillance audits conducted by an accredited certification body. The scope statement for the certificate identifies the services and locations included, and we will provide a copy of the current scope statement on request.

In addition to certification, Quillon commissions independent penetration tests of the platform, and these tests are performed by external firms that are separate from our own engineering staff. Independent penetration tests run once a year, and the findings from each test are tracked to resolution in our internal risk register. Severity ratings determine the target remediation window, and retesting confirms that high-severity findings have been closed before the next release that affects the relevant component.

Quillon also runs an internal vulnerability scanning program that operates continuously against production images, dependencies, and infrastructure configuration. Scan results feed the same tracking process as external findings, so that issues found by any source are triaged and assigned in one place.

## Data protection in transit and at rest

All connections between customer browsers, integrations, and the platform use encrypted transport. Connections from the public internet to the platform require modern transport encryption, and the platform rejects unencrypted requests to customer data endpoints. Internal service-to-service traffic within our production environment is also encrypted.

Contract documents, metadata, clause library content, and audit records are encrypted at rest using strong symmetric encryption. Encryption keys are managed through a dedicated key management service with access restricted to the systems that require them. Key rotation follows a documented schedule, and access to key management operations is logged and reviewed.

Customer data is stored in logically separated tenant partitions. Each customer's documents and metadata are scoped to that customer's tenant, and application-level checks enforce tenant boundaries on every request. Search across signed contracts operates only within the tenant of the authenticated user, and the search index is partitioned in the same way as the primary store.

## Access control and identity

Access to the platform for customer users is governed by role-based permissions configured by each customer's account administrator. Roles determine who can draft, edit, approve, sign, view, export, and administer contracts. Customers may enable single sign-on through their own identity provider, which allows them to enforce their existing password policies and multi-factor requirements. Session lifetimes and idle timeouts are configurable within limits that Quillon sets as minimums.

Quillon employees access production systems only through named accounts with multi-factor authentication. Access is granted on the basis of job role and reviewed periodically. When an employee changes roles or leaves the company, access is adjusted or removed promptly through a documented offboarding process. Privileged access to production data requires a justification, is time-limited where practical, and is recorded in audit logs.

Quillon does not require customers to share credentials with us, and our support staff access customer tenants only through mechanisms that are logged and visible to the customer's administrator when the customer has enabled that visibility.

## Audit logging and monitoring

The platform records a detailed audit trail of significant actions, including document creation, edits, approvals, signature requests and completions, permission changes, exports, and administrative configuration changes. Audit records are write-protected from ordinary application users and are retained for a period defined in the customer's agreement. Customers can export audit records for their own review and retention purposes.

Security monitoring covers authentication events, administrative actions, unusual access patterns, and changes to infrastructure configuration. Alerts are routed to on-call personnel who follow documented triage procedures. Where monitoring identifies behavior that may indicate account compromise, the affected sessions can be revoked and the account owner notified.

## Electronic signature integrity

Signatures collected through the platform are bound to the signed version of the document. Once a document is finalized for signature, its content is fixed, and any later change requires a new version that must be signed again. Completed signature packages include a record of signer identity checks, timestamps, and the audit events that led to completion. These records are designed to support the evidentiary use of signed contracts, although customers should consult their own counsel about the legal requirements that apply in their jurisdictions.

## Business continuity and resilience

The platform is deployed across multiple availability zones so that the failure of a single facility does not by itself interrupt service. Data is backed up on a regular schedule, and backups are encrypted and stored separately from the primary environment. Restoration procedures are tested periodically, and the results inform updates to our recovery runbooks.

Quillon maintains a business continuity plan that covers the loss of key facilities, personnel, and suppliers. The plan identifies critical functions, recovery priorities, and communication channels for customers. Customers who require specific availability commitments should refer to their service agreement, which sets out the commitments that apply to their subscription.

## Secure development

Changes to the platform go through peer review before merging. Automated tests and static analysis run as part of the build pipeline, and dependencies are scanned for known vulnerabilities. Changes that affect authentication, authorization, encryption, or handling of customer data receive additional review from the security team. Production deployments are logged, and the ability to deploy is restricted to authorized personnel.

Third-party components are evaluated before adoption, and we track their maintenance status and published vulnerabilities. When a serious vulnerability is disclosed in a component we use, we assess our exposure and prioritize updates accordingly.

## Vendor and subprocessor management

Quillon assesses the security practices of suppliers that handle customer data before engaging them and reviews those suppliers on a recurring basis. Contracts with suppliers include confidentiality and data protection obligations appropriate to the data they process. A current list of subprocessors that may process customer data is available to customers on request, along with notice of material changes as provided in the customer agreement.

## Incident response

Quillon maintains a documented incident response process that covers detection, containment, investigation, eradication, recovery, and lessons learned. Incidents are classified by severity, and the classification determines who is engaged and how quickly communication with affected customers begins. Where an incident is likely to affect customer data, we notify affected customers in accordance with the timelines in our customer agreement and applicable law. Post-incident reviews result in tracked corrective actions.

## Customer responsibilities and questions

Security is a shared responsibility. Customers should configure roles and approval chains to match their policies, enable single sign-on and multi-factor authentication where available, review audit logs periodically, and remove access promptly when staff change roles. Questions about this overview, requests for the current ISO 27001 scope statement, or requests for security questionnaire responses can be directed to the security team through the contact details published on our website. We review each request and respond through the appropriate channel.
