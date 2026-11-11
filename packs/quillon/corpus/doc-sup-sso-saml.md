---
title: Set up SAML single sign-on
audience: public
owner_scope: everyone
authority: guide
version_chain: sup-sso
effective_from: '2026-07-15'
supersedes: doc-sup-sso-2025
links:
- doc-plan-pro
- doc-sup-sso-enforce
type: support
doc_id: doc-sup-sso-saml
topics:
  cg-sso:
    about: SAML single sign-on
    claim: f-feat-sso
applies_to:
  product:
  - SAML single sign-on
  customer_group:
  - all
  from: '2026-07-15'
  to: null
---

# Set up SAML single sign-on

This guide explains how administrators on the Pro and Enterprise plans configure SAML 2.0 single sign-on (SSO) for Quillon. Once configured, users in your organization sign in to Quillon with the same credentials they use for your identity provider, and access can be granted or removed centrally.

## Prerequisites

Before you begin, confirm the following:

1. Your Quillon workspace is on the Pro and Enterprise plan, which includes SAML single sign-on.
2. You hold the workspace owner or administrator role in Quillon.
3. You have administrator access to your identity provider (IdP).
4. You have a SAML 2.0 metadata file from your IdP, or the metadata URL it publishes. Quillon accepts identity provider metadata files of up to 1 MB.
5. You have agreed with your IT or security team which user groups will be allowed to sign in through SSO.

We recommend testing the configuration with a small group of users before requiring SSO for the whole workspace.

## Gather the Quillon service provider details

Quillon acts as the service provider in this setup. Open **Settings, then Security, then Single sign-on** in your workspace. The page shows the values your IdP needs:

- **Entity ID:** the unique identifier for Quillon in your IdP.
- **Assertion consumer service URL:** the address your IdP posts sign-in responses to. On the SSO settings page this URL ends in /saml/acs.
- **Name ID format:** we recommend email address.

Keep this page open in a separate browser tab while you configure your IdP.

## Configure your identity provider

The steps differ slightly by provider. Follow the section that matches your IdP. In each case, enter the Quillon values from the previous section and map the user attributes listed below.

### Okta

1. In the Okta Admin Console, go to **Applications, then Applications, then Create App Integration**.
2. Choose **SAML 2.0** and select **Next**.
3. Enter Quillon as the app name and upload the logo if you wish.
4. Paste the assertion consumer service URL into the **Single sign-on URL** field and the entity ID into the **Audience URI** field.
5. Set the Name ID format to EmailAddress and the application username to Email.
6. Add attribute statements for email, first name and last name, mapping each to the matching user profile field.
7. Complete the setup, then assign the application to the user groups you agreed on.
8. Copy the Identity Provider metadata URL or download the metadata file and upload it in Quillon.

### Microsoft Entra ID

1. In the Microsoft Entra admin center, go to **Enterprise applications, then New application, then Create your own application**.
2. Choose the option to integrate a non-gallery application and name it Quillon.
3. Open **Single sign-on**, select **SAML**, and edit the **Basic SAML Configuration**.
4. Set the identifier to the entity ID and the reply URL to the assertion consumer service URL.
5. Under **Attributes and Claims**, confirm that the name identifier maps to the user principal name or email address, and add email, given name and surname claims.
6. Under **Users and groups**, assign the users or groups who should have access.
7. Download the Federation Metadata XML and upload it in Quillon.

### Google Workspace

1. In the Google Admin console, go to **Apps, then Web and mobile apps, then Add app, then Add custom SAML app**.
2. Enter Quillon as the app name and continue.
3. Copy the SSO URL and entity ID that Google displays, and download the IdP metadata file. Upload the metadata file in Quillon.
4. Back in Google, set the ACS URL to the assertion consumer service URL and the entity ID to the value from Quillon.
5. Map the Basic Information fields for first name, last name and primary email to the matching Google directory attributes.
6. Turn the app on for the organizational units or groups you agreed on.

## Test and enable SSO in Quillon

1. Return to **Settings, then Security, then Single sign-on** and upload your metadata file or paste the metadata URL.
2. Select **Test connection**. Quillon opens a sign-in window with your IdP. Sign in with a test account.
3. If the test succeeds, Quillon displays the account details it received. Confirm that the email address is correct.
4. Select **Enable SSO**. Users in the assigned groups can now sign in with the Single sign-on option on the Quillon login page.
5. Optionally, choose whether password sign-in remains available for workspace owners as a recovery route. We recommend keeping at least one owner account with password access.

Users who are not assigned to the Quillon application in your IdP will not be able to sign in through SSO, even if they have a Quillon account.

## Troubleshooting

Most problems come from a mismatch between the values in Quillon and those in the IdP, or from a clock difference between the two systems. Check the following before contacting support.

**Sign-in fails with a message about an invalid response.** Compare the entity ID and the assertion consumer service URL in your IdP with the values on the SSO settings page. Both must match exactly, including the trailing path.

**The metadata upload is rejected.** Confirm that the file is SAML 2.0 identity provider metadata and that it is no larger than 1 MB. Some providers offer a separate download for signing certificates only; use the full metadata file instead.

**Users are signed in with the wrong name or no email address.** Review the attribute mapping in your IdP and confirm that the email claim is present in every assertion.

**Error ERR-SAML-4012: assertion time outside allowed clock skew.** This error means the SAML assertion time is outside the allowed clock skew of 3 minutes between the identity provider and Quillon. Quillon rejects the sign-in attempt until the timestamps fall within that window. To resolve it, synchronize the clock on your identity provider with a network time source, then try again. If the error continues, ask your IT team to check whether the IdP is issuing assertions with an incorrect time zone or an expired validity window.

The table below summarizes the limits and values referred to in this guide.

| Item | Value |
|---|---|
| Plans that include SAML single sign-on | Pro and Enterprise |
| Maximum identity provider metadata file size | 1 MB |
| Allowed clock skew between identity provider and Quillon | 3 minutes |
| Assertion consumer service URL path | /saml/acs |
