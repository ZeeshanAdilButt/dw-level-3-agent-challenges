---
title: Integrations at a glance
audience: public
owner_scope: everyone
authority: guide
version_chain: integ-overview
effective_from: '2026-07-01'
supersedes: null
links:
- doc-integ-salesforce
- doc-integ-slack
type: integration
doc_id: doc-integ-overview
---

# Integrations at a glance

## Purpose of this guide

This guide summarizes the integrations available with Quillon, the contract-management platform used by law firms and corporate finance teams. It explains what each integration does and which plans can use it. Use it to decide which connections fit your team's workflow before you ask your administrator to enable them.

## Integration summary

The table below lists each integration, what it does, and the plans that can use it.

| Integration | What it does | Plans that can use it |
|---|---|---|
| Slack app | Posts contract activity and renewal alerts to Slack channels and lets users search contracts from Slack. | Team, Pro and Enterprise |
| Microsoft Teams app | Sends approval requests as cards in Teams so reviewers can act without opening Quillon. | Pro and Enterprise |
| Salesforce connector | Links contract records to Salesforce accounts and opportunities so sales teams can see contract status. | Pro and Enterprise |
| NetSuite connector | Links contract records to NetSuite customers and vendors so finance teams can match contracts to billing. | Pro and Enterprise |
| HubSpot connector | Links contract records to HubSpot companies and deals so account teams can see contract status. | Team plan and above |
| Okta sign-in | Lets users sign in to Quillon through Okta using SAML single sign-on. | Pro or Enterprise |

## Messaging integrations

The Slack app is available on the Team, Pro and Enterprise plans. Users can receive obligation and renewal notices in channels they already follow, and they can run searches across signed contracts without leaving Slack.

The Microsoft Teams app sends approval requests as cards, which lets reviewers approve or comment from within Teams. The Microsoft Teams app is available on the Pro and Enterprise plans.

## CRM integrations

The Salesforce connector is available on the Pro and Enterprise plans. It keeps contract records associated with the correct accounts and opportunities, which helps sales operations confirm that signed terms match what was sold.

The HubSpot connector is available on the Team plan and above. It provides a similar link for companies and deals, so account teams can check contract status without switching systems.

## Finance integrations

The NetSuite connector is available on the Pro and Enterprise plans. Finance teams can link contracts to customer and vendor records, which supports reconciliation between agreed terms and invoiced amounts.

## Identity and access

Okta sign-in uses SAML, so it needs the Pro or Enterprise plan. Once enabled, users sign in with their corporate Okta credentials, and access can be managed centrally through the identity provider.

## Choosing an integration

Start with the system where your team already works most often. Sales operations teams usually begin with the Salesforce or HubSpot connector, finance teams with the NetSuite connector, and legal and procurement teams with the Slack or Microsoft Teams app for approvals and alerts. If your organization requires centralized sign-in, confirm that your plan includes Okta sign-in before planning the rollout.

## Getting help

Your Quillon administrator can enable integrations and confirm plan eligibility. For questions about setup steps, contact Quillon support through the help center in the product.
