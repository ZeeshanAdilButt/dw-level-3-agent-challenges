---
title: Enforce single sign-on
audience: public
owner_scope: everyone
authority: guide
version_chain: sup-sso-enforce
effective_from: '2026-07-15'
supersedes: null
links:
- doc-sup-sso-saml
type: support
doc_id: doc-sup-sso-enforce
---

# Enforce single sign-on

Effective from 2026-07-15

## Overview

Single sign-on (SSO) lets your users sign in to Quillon with the identity provider your organisation already uses. When SSO is enforced, users can no longer sign in with a Quillon password. The one exception is break-glass access: when SSO is enforced, password sign-in stays open for 2 designated break-glass admins so that your workspace remains reachable if the identity provider is unavailable.

## Before you begin

- Confirm that your identity provider is connected and that a test sign-in succeeds.
- Choose 2 designated break-glass admins and confirm that each one knows their Quillon password.
- Tell your users that sign-in will change for their workspace.

## Steps to enforce SSO

1. Sign in to Quillon as a workspace owner.
2. Open Settings, then select Security.
3. Select Single sign-on and confirm that your identity provider shows as connected.
4. Turn on Enforce single sign-on.
5. Review the list of break-glass admins and confirm that it contains the 2 designated admins.
6. Select Save to apply the change.
7. Ask one of the break-glass admins to sign in with a password to confirm that break-glass access works.

## Tip

Keep the 2 break-glass admin accounts in active use at least once each quarter. This confirms that their passwords and multi-factor methods still work when you need them most.

## Need help?

Contact the Quillon support team from the Help menu in your workspace.
