---
title: Salesforce connector
audience: public
owner_scope: everyone
authority: guide
version_chain: integ-salesforce
effective_from: '2026-07-01'
supersedes: null
links:
- doc-sup-sync-errors
- doc-plan-pro
type: integration
doc_id: doc-integ-salesforce
---

# Salesforce connector

## Overview

The Salesforce connector links Quillon with Salesforce so that contract records, account details, and opportunity information can move between the two systems without manual re-entry. Sales operations teams, legal teams working with commercial agreements, and finance teams that track contract values against customer accounts are the main audiences for this integration. Once connected, a contract created or updated in Quillon can reflect on the matching Salesforce account, and key Salesforce fields can seed new contract drafts in Quillon.

The connector is designed for teams that already use Salesforce as their system of record for customers and deals, and that want legal and finance documents to stay aligned with those records. It does not replace Salesforce workflows. Instead, it keeps the contract lifecycle in Quillon and the commercial pipeline in Salesforce in step with each other.

## Who can use the connector

The connector is available on the Pro and Enterprise plans. Administrators on those plans can enable it from the integrations area of the workspace settings. Users who do not hold an administrator role can request access, but an administrator must complete the initial authorization. Organizations on plans below Pro do not see the connector in the integrations catalog and cannot install it without a plan change.

Before enabling the connector, confirm that the Salesforce user who will authorize the link has permission to read and write the objects you plan to sync, such as accounts, opportunities, and contracts. Quillon can only sync the objects and fields that the authorizing Salesforce user can access. If the connector reports missing permissions during setup, adjust the Salesforce profile or permission set before trying again.

## What the connector syncs

The connector moves information in both directions, though not every field travels the same way. Account names, identifiers, and primary contacts are read from Salesforce and matched to parties in Quillon. Contract status, effective dates, renewal dates, and the link to the signed document are written from Quillon back to the related Salesforce record. Opportunity values can be pulled into a contract draft so that pricing terms start from the figures already agreed in the deal.

Sync runs on a fixed schedule. The Salesforce connector syncs every 15 minutes, so a change made in one system appears in the other within that window. Changes made in Quillon, such as a contract being signed, typically appear in Salesforce on the next scheduled run. If you need a record to update sooner, use the manual sync option on the individual contract or account, which runs an immediate sync for that record only.

Because sync is scheduled rather than instant, avoid relying on the connector for time-critical handoffs within a single minute. For example, if a Salesforce workflow must trigger the moment a contract is signed, build that trigger on the Quillon webhook events instead of expecting the connector to act in real time.

## Setup steps

1. Sign in to Quillon as a workspace administrator and open the integrations area from the workspace settings menu.
2. Select the Salesforce connector and choose Connect. You will be redirected to Salesforce to sign in.
3. Sign in with a Salesforce user who has read and write access to the accounts, opportunities, and contract objects you intend to sync. Approve the access request when Salesforce prompts you.
4. Return to Quillon and confirm that the connection status shows as connected. If the status shows an error, review the message, correct any permission issues in Salesforce, and reconnect.
5. Map Salesforce accounts to Quillon parties. Quillon proposes matches based on account name and identifier. Review each proposed match and confirm, correct, or skip it. Unmatched accounts remain in Salesforce only until mapped.
6. Choose which Salesforce fields should populate contract drafts, such as account name, billing contact, and opportunity amount. Fields you do not select are not read from Salesforce.
7. Choose which Quillon contract fields should write back to Salesforce, such as contract status and signed document link. Keep write-back limited to the fields your sales operations team needs.
8. Run a manual sync on one test account and check the result in both systems. Confirm that the values match and that the signed document link opens correctly from the Salesforce record.
9. Enable the scheduled sync. Records will then sync every 15 minutes according to the mappings you configured.

## Limits and known constraints

The connector works with the standard Salesforce objects covered by the mapping screens. Custom objects are not supported in the initial release, and any custom fields must be surfaced through the field mapping step to be used. Large initial syncs can take longer than a normal scheduled run, so schedule the first full sync outside peak sales hours where possible.

Each Salesforce record can map to one Quillon party at a time. If two Salesforce accounts share the same legal entity, map only one of them and note the relationship in the Salesforce record for your team. Deleted records in Salesforce are not automatically removed from Quillon. Instead, they are flagged for review so that signed contracts are never lost by accident.

Sync conflicts occur when the same field changes in both systems between runs. Quillon keeps the most recent change and logs the overwritten value in the connector activity log, which administrators can review. For fields where Salesforce should always be authoritative, such as account owner, set the field to read-only in Quillon so the conflict cannot arise.

## Troubleshooting

If a sync fails, check the connection status first. An expired authorization is the most common cause and is resolved by reconnecting. If records are missing, confirm that the Salesforce user still has access to the relevant objects and that the account mapping has been confirmed. The connector activity log records each run with its outcome, the number of records processed, and any errors, and it is the first place to look when behavior seems inconsistent.

For issues that persist after these checks, contact Quillon support through the help menu and include the connector activity log entry for the affected run.
