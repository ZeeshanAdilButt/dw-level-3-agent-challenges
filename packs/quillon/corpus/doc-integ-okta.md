---
title: Okta sign-in
audience: public
owner_scope: everyone
authority: guide
version_chain: integ-okta
effective_from: '2026-07-01'
supersedes: null
links:
- doc-sup-sso-saml
type: integration
doc_id: doc-integ-okta
---

# Okta sign-in

## Overview

Okta sign-in lets your users access Quillon using the single sign-on (SSO) identity provider your organization already runs. Users sign in with their existing Okta credentials and multi-factor settings, and Quillon does not store their Okta passwords. This guide describes what the integration does, who can use it, how to set it up, and the limits to plan for.

Okta sign-in uses SAML, so it needs the Pro or Enterprise plan. Accounts on other plans cannot enable it, and administrators should confirm their plan before starting setup.

## Who can use it

The integration is available to Quillon workspace administrators who also hold administrative rights in the Okta tenant. Both roles are needed because setup requires changes on each side: the Quillon workspace settings and the Okta application configuration.

End users need only an active Okta account assigned to the Quillon application. Once assigned, they sign in from the Quillon login page using the organization sign-in option and are redirected to Okta.

## What the integration does

- Routes sign-in requests from Quillon to Okta for authentication.
- Applies the authentication policies you already configure in Okta, including multi-factor prompts.
- Creates a Quillon user on first sign-in when the user is assigned to the application, if provisioning is enabled.
- Ends the Quillon session when the user signs out of Quillon, and honors Okta session timeouts.

It does not synchronize contract data with Okta, and it does not grant permissions inside Quillon by itself. Roles such as drafter, approver, or read-only viewer are still assigned within Quillon.

## Setup steps

1. In the Okta admin console, create a new SAML 2.0 application for Quillon and choose the option to enter the configuration manually.
2. Open Quillon workspace settings, select Single sign-on, and copy the Assertion Consumer Service URL and the Entity ID shown there.
3. Paste those values into the matching fields of the Okta SAML application and save.
4. Set the name ID format to email address and map the email attribute to the user's primary Okta email.
5. Download the identity provider metadata or copy the sign-on URL and signing certificate from Okta.
6. Return to Quillon workspace settings and paste the Okta sign-on URL, Issuer, and signing certificate into the identity provider fields.
7. Select Test connection. Quillon opens a sign-in window against Okta; complete the sign-in with a test account.
8. Assign the Okta application to the users or groups who should have access.
9. Enable Require single sign-on in Quillon only after the test account and at least one other administrator have signed in successfully. This prevents lockout.
10. Ask a sample of users to sign in from the Quillon login page and confirm they reach their workspace.

Keep at least one local administrator account in Quillon until you have confirmed that single sign-on works for every administrator who needs it.

## Limits and things to know

- Okta sign-in is available only on the Pro and Enterprise plans, as noted above.
- Users must have an email address that matches their Quillon account. If the email differs, sign-in creates a separate account or fails, depending on provisioning settings.
- Changes to a user's Okta assignment take effect at their next sign-in. Removing a user from the Okta application does not immediately end an active Quillon session.
- Certificate rotation in Okta requires updating the signing certificate in Quillon before the old certificate expires, or sign-in will fail for all users.
- Quillon supports SAML-based sign-in only for this integration. Other Okta protocols are not covered by this guide.

For questions about your plan or certificate schedule, contact your Quillon account team before making changes in production.
