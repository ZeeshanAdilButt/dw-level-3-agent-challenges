---
title: NetSuite connector
audience: public
owner_scope: everyone
authority: guide
version_chain: integ-netsuite
effective_from: '2026-07-01'
supersedes: null
links: []
type: integration
doc_id: doc-integ-netsuite
---

# NetSuite connector

## Purpose and scope

The Quillon NetSuite connector links the contract records held in Quillon with the vendor and purchasing records kept in Oracle NetSuite. Legal, procurement, and finance teams use it so that a contract signed in Quillon is visible to the people who manage suppliers, payments, and spending inside NetSuite, and so that changes made on either side are reflected where they are needed. The connector is an integration guide for administrators and integration leads. It describes what the connector does, who can use it, how to set it up, and the limits to plan around.

Quillon contract records cover drafts, approved agreements, executed agreements with e-signature evidence, and the obligations, renewal dates, and clauses attached to each one. NetSuite holds the vendor master file, purchase orders, and accounts payable records. The connector does not move the full contract body into NetSuite. It creates and maintains a shared reference between the two systems so that each side can find the other.

## Who can use the connector

The NetSuite connector is available on the Pro and Enterprise plans. Organizations on other plans cannot enable it, and the connector panel does not appear in the administration console for those accounts. Before planning a project, confirm the plan with your account owner so that expectations about timing and scope are set correctly.

Within an eligible account, enabling and configuring the connector requires the Integration Administrator role in Quillon and a NetSuite user with permission to create integration credentials and to read and write vendor records. The NetSuite user should be a dedicated integration account rather than a personal login, so that the connection continues to work when staff change roles.

## What the connector does

The connector links each contract to a vendor record in NetSuite. When a contract is created in Quillon, the user selects the counterparty, and the connector looks for a matching vendor record in NetSuite using the vendor name, tax identifier, and any configured external identifier. If a single match is found, the contract is linked to that vendor record automatically. If several candidates appear, the user is asked to choose one, and the choice is saved so that future contracts with the same counterparty are linked consistently.

Once a link exists, the connector performs the following actions:

- It writes the Quillon contract identifier, the contract title, and the contract status into a custom field on the NetSuite vendor record.
- It posts the effective date, expiry date, and next renewal date from Quillon into the same custom record, so that procurement users can see when a supplier relationship will need attention.
- It marks the vendor record when a contract has been executed, with the date of execution taken from the e-signature completion record.
- It sends a notification from Quillon to the contract owner when a linked NetSuite vendor record is made inactive, so that the contract can be reviewed.

The connector reads certain NetSuite data back into Quillon. It refreshes vendor names and addresses when they change in NetSuite, provided the change is made in the vendor master file and not in a Quillon contract. It does not change payment terms, approval limits, or purchase order content in Quillon, because those values belong to the finance record of truth. Where a contract stores payment terms that differ from the NetSuite vendor record, Quillon shows both values and flags the difference for review without overwriting either one.

Synchronization runs on a schedule set by the administrator and can also be triggered manually from the connector panel. Changes made in Quillon are normally reflected in NetSuite within the synchronization window, and changes in NetSuite are read back on the same cycle.

## Setup steps

Follow these steps in order. Most setup problems come from skipping the credential check or the field mapping, so complete both before enabling synchronization for the whole organization.

1. Confirm that your account is on the Pro or Enterprise plan. Open the administration console and check that the NetSuite connector section is visible. If it is not visible, contact your account owner before continuing.
2. In NetSuite, create a dedicated integration role with read and write access to vendor records, custom vendor fields, and the integration record type. Assign this role to a dedicated integration user.
3. In NetSuite, enable token-based authentication for the integration and generate the consumer key, consumer secret, token ID, and token secret for the integration user. Record these values in your organization's secrets store. Do not paste them into shared documents or tickets.
4. In NetSuite, create the custom fields that Quillon will populate on the vendor record: contract identifier, contract status, effective date, expiry date, next renewal date, and execution date. Note the internal identifiers of each field, as you will need them in the mapping step.
5. In Quillon, open the NetSuite connector panel and enter your NetSuite account identifier, the environment (production or sandbox), and the credentials from step 3. Save the configuration and run the connection test. A successful test confirms that the credentials, role permissions, and network path are working.
6. Map each Quillon contract field to the matching NetSuite custom field using the internal identifiers recorded in step 4. Check that date fields are mapped to date fields and that status values are mapped to a list of allowed values in NetSuite.
7. Choose a matching rule for vendors. The default rule uses the vendor name and tax identifier. If your NetSuite vendor master uses an external identifier, add it as a secondary matching key. Run a dry run against a sample of recent contracts and review the proposed links before accepting them.
8. Start with a pilot group of contract owners and a single subsidiary or business unit. Enable synchronization for the pilot, review linked records for at least one full synchronization cycle, and correct any mapping issues before extending the connection to other teams.
9. Enable scheduled synchronization for the full organization once the pilot results are satisfactory. Record the schedule and the name of the person responsible for monitoring the connection in your internal runbook.

## Limits and things to plan for

The connector synchronizes references and key dates, not the full text of contracts or attachments. Users who need the executed document must open it in Quillon. NetSuite users who need to read contract terms should be given a link to the Quillon record and access to Quillon, rather than expecting the terms to appear in NetSuite.

Each Quillon contract can be linked to one NetSuite vendor record. Contracts that cover several vendors, such as a framework agreement with multiple suppliers, must be linked to a primary vendor record, with the remaining vendors recorded in the contract notes. If a contract needs to be linked to multiple vendor records as a regular pattern, raise this with your account owner before rollout.

Synchronization is not instantaneous. Changes take effect on the next cycle, and a failed cycle is retried automatically. Failures, including expired credentials, changed field identifiers in NetSuite, or revoked role permissions, are shown in the connector panel and sent to the Integration Administrator. Reauthorize credentials before they expire, and avoid renaming or deleting mapped custom fields in NetSuite without first updating the mapping in Quillon.

Deleting a Quillon contract does not delete the corresponding NetSuite custom field values automatically. The connector clears the linked fields on the next synchronization cycle and records the change in its activity log. Deleting or merging vendor records in NetSuite breaks existing links, and Quillon reports these as unresolved links for manual repair.

For questions about setup, plan eligibility, or unresolved links, contact Quillon support through the administration console and include the connector activity log for the period in question.
