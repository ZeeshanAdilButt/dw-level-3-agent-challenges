---
title: Microsoft Teams app
audience: public
owner_scope: everyone
authority: guide
version_chain: integ-teams
effective_from: '2026-07-01'
supersedes: null
links: []
type: integration
doc_id: doc-integ-teams
---

# Microsoft Teams app

## Purpose

The Microsoft Teams app connects Quillon to Microsoft Teams so that contract approvals, status updates, and renewal reminders reach the people who need them without leaving the chat tool. It is designed for law firm teams and corporate finance teams that already coordinate work in Teams and want contract decisions to happen where the conversation already is.

The app sends approval requests as cards, which show the contract name, the requester, the counterparty, the key dates, and buttons to approve, request changes, or open the full record in Quillon. Approvers can act on a card directly in Teams, and every decision is written back to the contract record in Quillon with a timestamp and the approver's name.

## Who can use it

The Microsoft Teams app is available on the Pro and Enterprise plans. Customers on other plans can continue to use Quillon in the browser but will not see the Teams app in their available integrations.

A Quillon administrator installs the app for the organization. Individual users then connect their own Quillon account to Teams, so that actions taken in Teams are attributed to the correct person and respect their existing permissions. A user who cannot see a contract in Quillon will not be able to act on its card in Teams.

## Features

The app supports four main functions:

- Approval cards: requests from the approval workflow arrive in the relevant channel or in a direct message, depending on how the workflow is configured.
- Renewal alerts: upcoming renewal and notice dates are posted to a chosen channel ahead of the deadline.
- Obligation reminders: tracked obligations that fall due, such as delivery milestones or reporting requirements, can be sent to the responsible owner.
- Search: users can search signed contracts from the Teams message box and receive a summary with a link to the full record.

Drafting, clause editing, and e-signature remain in Quillon. Teams cards link back to Quillon for those steps.

## Setup steps

1. Confirm that your organization is on the Pro or Enterprise plan and that you hold the administrator role in Quillon.
2. In Quillon, open Settings, then Integrations, and select Microsoft Teams.
3. Select Install and sign in with a Microsoft account that has permission to add apps to your Teams tenant. If the install is blocked, ask your Microsoft 365 administrator to approve the Quillon app.
4. Choose the default channels for approval cards and renewal alerts. You can change these later for each workflow.
5. Ask each user to open the Quillon app in Teams, select Connect account, and sign in to Quillon.
6. Send a test approval request from a sample contract to confirm that the card appears and that the decision is recorded in Quillon.
7. Review the notification settings for each user so that alerts reach the right people without duplication.

## Limits

- Cards show a summary only. Full clause text, redlines, and attachments must be viewed in Quillon.
- An approval can be recorded in Teams only if the approver has edit rights on the contract in Quillon.
- Search results in Teams cover signed contracts only. Drafts and contracts in review are available only in Quillon.
- Teams notifications depend on Microsoft's delivery service. Quillon retries failed messages but cannot guarantee delivery time.
- The app does not replace the approval audit trail in Quillon, which remains the record of truth for compliance purposes.
- Changes to the Teams tenant, such as blocked app permissions, may stop the integration until an administrator restores access.
