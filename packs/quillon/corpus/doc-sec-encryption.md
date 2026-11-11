---
title: Encryption
audience: public
owner_scope: everyone
authority: rule
version_chain: sec-encryption
effective_from: '2026-07-01'
supersedes: null
links: []
type: security
doc_id: doc-sec-encryption
---

# Encryption

## Purpose and scope

This document describes how Quillon protects customer data through encryption, both while it is stored and while it moves between systems and to users. It covers the contract-management platform as a whole, including drafting from templates, the clause library, approval workflows, electronic signature, obligation tracking, renewal alerts, and search across signed agreements. Encryption applies to all customer content, metadata derived from that content, and the operational records that describe customer activity. The security team reviews this document as part of the regular control review, and any change to the controls described here will be reflected in a new revision before it takes effect.

Customers in law firms and corporate finance teams often handle privileged, confidential, or material non-public information within their agreements. For that reason, encryption is treated as a baseline control rather than an optional feature. The controls below apply to every customer, regardless of plan, unless a specific section states otherwise.

## Scope of protected data

Protected data includes uploaded contract files, drafts generated from templates, clause library entries that a customer has created or modified, approval comments, signature certificates, obligation and renewal records, and search indexes built from customer documents. Quillon's own account data, such as user names, billing contacts, and administrative settings, is also encrypted under the same standards. Search indexes receive the same protection as the documents they describe, because an index can reveal the contents of a document even without the original file.

Backups, replicas, and log archives that contain customer data are encrypted in the same way as primary storage. Temporary files created during document conversion or text extraction are written to encrypted storage and are deleted after processing completes.

## Data at rest

All customer data stored in Quillon's production systems is encrypted at rest with AES-256. The encryption applies to databases, object storage holding document files, search indexes, backup media, and replicated storage in secondary locations. Encryption is performed by the storage layer, and application code does not handle unencrypted data in persistent storage.

Each stored data object is encrypted with a data key, and those data keys are themselves encrypted with a master key held in a dedicated key management service. Master keys are rotated on a scheduled basis, and rotation does not require re-uploading customer documents. Access to key management functions is restricted to a small set of service identities and to named members of the security team, and every use of a master key is logged.

Decryption of customer data occurs only when an authorized request requires it, such as a user opening a document, a signature workflow reading a file, or a search query returning results. Decrypted content is held in memory for the duration of the request and is not written to unencrypted disk.

## Data in transit

All network traffic that carries customer data uses TLS 1.3. This includes connections from web browsers and desktop clients to the Quillon application, API calls made by customer integrations, connections between Quillon's internal services, and transfers to subprocessors that receive customer data for the purpose of providing the service. Connections that offer only older protocol versions are refused.

Certificates are issued by a publicly trusted authority, and certificate lifecycles are monitored so that expiry does not interrupt service. Internal service traffic is also encrypted and authenticated, so that a compromised network segment does not expose customer content in cleartext.

Email notifications sent by Quillon, such as renewal alerts and approval requests, contain only limited information and direct the recipient to an authenticated page to view the underlying document. Where a recipient's mail system supports encrypted transport, Quillon uses it, but the content of the notification itself is designed so that the agreement's text is not included in the message body.

Electronic signature requests are delivered through authenticated links. The signing session is encrypted in transit, and completed signature certificates are stored with the same protections as the signed document.

## Customer-managed encryption keys

By default, Quillon manages the master keys that protect customer data, as described above. Customer-managed encryption keys are available on the Enterprise plan only. Under this option, the customer supplies and controls a key in its own key management system, and Quillon uses that key to protect the customer's data encryption keys.

Customers who use this option retain the ability to revoke Quillon's access to the key. When access is revoked, Quillon can no longer decrypt the customer's data, and the service for that customer stops functioning until access is restored. Customers should plan key rotation and revocation procedures with their own security staff before enabling the feature, and Quillon provides documentation to support that planning.

Customer-managed keys are not available on other plans. Customers on other plans who require control over their own keys should contact their account representative to discuss the options available under their agreement.

## Key management and access

Quillon maintains separate key hierarchies for production, staging, and backup environments, so that a compromise in a non-production environment cannot expose production key material. Keys are never embedded in application source code, configuration files, or container images. Application services obtain the keys they need at runtime through authenticated requests to the key management service, and those requests are restricted by role.

Engineers do not have standing access to decrypt customer data. Access to production data for support or incident response requires a documented request, approval from an authorized reviewer, and a time-limited grant. Each grant is recorded, and the records are reviewed by the security team.

## Summary of controls

The following table summarizes the encryption controls described in this document.

| Area | Control |
|---|---|
| Data at rest | Encrypted with AES-256 |
| Data in transit | Encrypted with TLS 1.3 |
| Customer-managed keys | Enterprise plan only |
| Master key rotation | Scheduled, without re-uploading documents |
| Backups and replicas | Encrypted using the same standards as primary storage |
| Production data access | Requires documented request and time-limited approval |

## Questions and reporting

Customers with questions about these controls, or who want to review evidence supporting them, can contact their account representative or the Quillon security team through the security contact listed in the customer portal. Suspected weaknesses in encryption or key handling should be reported through the same channel, and reports are reviewed promptly by the security team.
