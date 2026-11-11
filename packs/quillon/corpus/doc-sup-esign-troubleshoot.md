---
title: Signing problems and fixes
audience: public
owner_scope: everyone
authority: guide
version_chain: sup-esign-troubleshoot
effective_from: '2026-07-15'
supersedes: null
links:
- doc-prod-esign
type: support
doc_id: doc-sup-esign-troubleshoot
---

# Signing problems and fixes

Effective from 2026-07-15

## Overview

This guide covers the most common problems that stop a contract from being signed in Quillon, and the steps to fix them. Most signing problems come from an expired signing link, a signer who has not received the request, or an envelope that was sent to the wrong address. Work through the steps in order, and stop once the problem is resolved.

## When a signing link no longer works

If a signer sees an error when opening the link in their email, the link has probably expired. Error code ERR-SIG-308 means the signing link has expired, so the envelope must be sent again before the signer can complete the document.

1. Sign in to Quillon and open the contract list.
2. Select the contract that is waiting for signature.
3. Open the envelope page for that contract.
4. Find the signer who reported the problem.
5. Select Resend link. Quillon creates a new signing link and emails it to the signer.
6. Ask the signer to open the newest email only. Older links will not work.

## When a signer has not received the request

Sometimes the signing request lands in a spam folder or is sent to an old address.

1. On the envelope page, check the email address listed for the signer.
2. Correct the address if it is wrong, then select Resend link.
3. Ask the signer to check spam, junk, and promotions folders.
4. If the signer still cannot find the email, copy the signing link from the envelope page and send it to them through a channel you trust.

## When a signer needs a reminder

Quillon can remind signers automatically. Automatic signer reminders go out every 3 days until the envelope is complete or cancelled. You do not need to set this up for each contract. If a signer is still outstanding after several reminders, contact them directly, because a reminder cannot replace a personal follow-up.

## When the document shows the wrong fields

If a signer sees a missing signature box or a field in the wrong place, do not ask them to sign yet. Return to the draft, correct the field placement, and send the envelope again. Signers who signed an incorrect version may need a fresh envelope so that the record stays accurate.

## Tip

Before sending any envelope, open the signer view yourself using the preview option. This shows you exactly what each signer will see, and it catches wrong fields and wrong addresses before they cause delays.

## Still stuck?

If none of these steps resolves the problem, contact the Quillon support team through the help option in the product. Include the contract name, the signer's email address, and the error code shown on screen. This information lets us find the envelope quickly and reply with a specific fix.
