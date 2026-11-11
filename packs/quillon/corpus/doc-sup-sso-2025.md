---
title: Set up single sign-on (2025)
audience: public
owner_scope: everyone
authority: guide
version_chain: sup-sso
effective_from: '2025-04-01'
supersedes: null
links: []
type: support
doc_id: doc-sup-sso-2025
topics:
  cg-sso:
    about: SAML single sign-on
    claim: f-sso-old-team
applies_to:
  product:
  - SAML single sign-on
  customer_group:
  - all
  from: '2025-04-01'
  to: '2026-07-14'
---

# Set up single sign-on (2025)

This support guide explains how administrators can connect Quillon to their identity provider so that users sign in with their existing company credentials. It applies from 2025-04-01.

## Before you begin

SAML single sign-on is available on Team and above. If your workspace is on a different plan, contact your account manager before starting. You will need administrator access to Quillon and to your identity provider (for example, a directory service or corporate identity platform).

## Setup steps

1. Sign in to Quillon as a workspace administrator.
2. Open Settings, then select Security, then select Single sign-on.
3. Choose SAML as the sign-in method.
4. Copy the Quillon entity ID and the assertion consumer service URL shown on the page.
5. In your identity provider, create a new SAML application and paste the entity ID and assertion consumer service URL.
6. Map the email attribute to the user's sign-in email address, and map the name attribute to the user's full name.
7. Download the metadata file or copy the sign-in URL and certificate from your identity provider.
8. Return to Quillon, paste the sign-in URL and certificate into the matching fields, and select Save.
9. Select Test connection. A successful test opens a sign-in window and returns you to Quillon.
10. Turn on Require single sign-on for all users once the test succeeds.

## Troubleshooting

If the test fails, check that the entity ID matches exactly and that the certificate has not expired. Attribute mapping errors are the most common cause of sign-in problems.

## Tip

Keep one administrator account with password sign-in enabled, so you can still reach the workspace if the identity provider is unavailable.
