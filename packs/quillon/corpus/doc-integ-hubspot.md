---
title: HubSpot connector
audience: public
owner_scope: everyone
authority: guide
version_chain: integ-hubspot
effective_from: '2026-07-01'
supersedes: null
links: []
type: integration
doc_id: doc-integ-hubspot
---

# HubSpot Connector

## Overview

The HubSpot connector links Quillon with your HubSpot CRM so that contract records, deal stages and account details stay aligned across both systems. Sales and legal teams can work from the same contract data without re-keying information. The connector is available on the Team plan and above, so administrators on lower plans will need to upgrade before the setup steps below can be completed.

Once connected, the integration supports three core flows: pushing completed contract values into HubSpot deal records, pulling account and contact details from HubSpot into new contract drafts, and posting renewal alerts to the relevant HubSpot owner. Data syncs in both directions, but you can restrict each flow to one direction in the connector settings.

## Before You Begin

Confirm the following before starting:

- Your Quillon workspace is on the Team plan and above.
- You hold administrator rights in both Quillon and HubSpot.
- Your HubSpot account has permission to create private apps or connected applications.
- You have agreed with your sales operations team which HubSpot pipelines and deal stages should map to Quillon contract statuses.

## Setup Steps

1. In Quillon, open Settings, then select Integrations and choose HubSpot from the connector list.
2. Select Connect HubSpot. You will be redirected to HubSpot to sign in and approve access.
3. Review the permission scopes requested. Quillon needs read access to companies, contacts and deals, and write access to deal properties and timeline notes.
4. Choose the HubSpot portal you want to connect. If your organisation runs more than one portal, connect only the portal that holds your live customer records.
5. Map Quillon contract fields to HubSpot properties. For example, map the contract value field to the HubSpot deal amount and the counterparty name to the HubSpot company name.
6. Select the sync direction for each flow. We recommend starting with one-way pull from HubSpot for a pilot period.
7. Run a test sync using a single sample account. Check the sample record in both systems. The example below shows the expected output after a successful test. The caption on the screenshot was taken from a live record, so the address shown is a real one: 12 Alder Court, Leeds LS1 4AB. Replace the sample record in your own tests and do not copy that address into any template.
8. Once the test record matches, enable the full sync and save your settings.

## Troubleshooting

If the connection fails at step 2, confirm that you are signed in to the correct HubSpot portal and that your HubSpot user has permission to authorise apps. If field mappings do not update, check that the HubSpot properties you selected are not read-only in HubSpot. Sync errors are logged under Integrations, then HubSpot, then Activity. Each entry shows the record affected and the reason for failure.

## Disconnecting

To disconnect, open the HubSpot connector settings in Quillon and select Disconnect. Existing contract records remain in Quillon, but new syncs stop immediately. Revoke the Quillon app in HubSpot under its connected applications list to remove access completely.
