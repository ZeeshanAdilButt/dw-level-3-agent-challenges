---
title: Two-step verification
audience: public
owner_scope: everyone
authority: guide
version_chain: sup-mfa
effective_from: '2026-07-15'
supersedes: null
links: []
type: support
doc_id: doc-sup-mfa
---

# Two-step verification

## Overview

This guide explains how to turn on two-step verification for your Quillon account, how to add a second factor, and what to do if you lose access to that factor. Two-step verification adds a second check after your password, so a stolen password alone is not enough to sign in to contract records, approval queues, or signed-contract search.

Quillon supports authenticator apps and WebAuthn security keys but not SMS codes. If you were expecting text message codes, use an authenticator app or a security key instead. Authenticator apps generate a six-digit code on your device, and WebAuthn security keys confirm your sign-in with a touch or PIN.

## Who can enable it

Account owners and administrators can require two-step verification for everyone in their organization. Individual users can also enable it for their own sign-in at any time. Firm-wide enforcement is recommended for law firms and corporate finance teams that store executed agreements, because those teams often handle confidential terms, payment obligations, and renewal dates.

## Setting up an authenticator app

1. Sign in to Quillon with your username and password.
2. Open your profile menu and select Security.
3. Select Add second factor, then choose Authenticator app.
4. Open your authenticator app on your phone and scan the QR code shown on screen. If scanning fails, choose Enter setup key and type the key manually.
5. Enter the six-digit code your app displays. The code changes every thirty seconds, so enter the current one.
6. Save the recovery codes Quillon displays. Store them somewhere secure that is not on the same phone as your authenticator app.
7. Select Finish. The new factor is now active for your next sign-in.

## Setting up a WebAuthn security key

1. Sign in and open Security from your profile menu.
2. Select Add second factor, then choose Security key.
3. Insert your WebAuthn-compatible key into a USB port or bring it near your device, as your key requires.
4. Follow the prompt from your browser or operating system to create a credential, which may include setting a PIN on the key.
5. Give the key a name you will recognize later, such as "Office key" or "Travel key."
6. Select Finish. Register at least two keys or one key plus an authenticator app so you are not locked out if one device is lost.

## Signing in with a second factor

After you enter your password, Quillon asks for your second factor. For an authenticator app, enter the current six-digit code. For a security key, insert or tap the key and confirm. You can choose Trust this device for a period set by your administrator, after which the second factor is requested again.

## Troubleshooting

**I lost my phone.** Use one of your saved recovery codes to sign in, then go to Security, remove the old authenticator, and add a new one. If you have no recovery codes and no other factor, contact your account administrator, who can reset your second factor after confirming your identity. Quillon support cannot reset factors for administrators or for accounts without a verified contact.

One example from our support queue shows why it matters to save recovery codes in advance: "Customer called from +1 202 555 0147 after losing their phone." Support staff verified the request through the account owner before resetting the factor, which took longer than it would have with a saved recovery code.

**My security key is not recognized.** Confirm the key is WebAuthn-compatible, try a different USB port, and check that your browser has permission to use security keys. Remove the key from Security and register it again if the problem continues.

**My codes are rejected.** Check that your device clock is set to automatic time. Authenticator codes depend on accurate time, and a drifting clock is the most common cause of rejected codes.

## Getting help

Contact your account administrator first. If they cannot help, contact Quillon support through the Help menu and include your account name and the steps you have already tried. Do not send recovery codes or full security keys in a support request.
