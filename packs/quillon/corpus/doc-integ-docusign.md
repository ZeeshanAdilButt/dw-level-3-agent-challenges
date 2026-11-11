---
title: DocuSign import
audience: public
owner_scope: everyone
authority: guide
version_chain: integ-docusign
effective_from: '2026-07-01'
supersedes: null
links: []
type: integration
doc_id: doc-integ-docusign
---

# DocuSign import

## Purpose

This guide explains how the DocuSign import feature in Quillon brings completed DocuSign envelopes into your contract library. Once imported, signed agreements become searchable alongside contracts drafted in Quillon, and they can be tracked for obligations and renewal dates. This page is written for administrators and contract owners who set up the connection.

## What the import does

The DocuSign import brings in completed envelopes from the last 5 years. Only envelopes with a status of completed are imported. Envelopes that are still out for signature, declined, or voided are not included, so you will not see partial or abandoned agreements in your library.

For each imported envelope, Quillon stores the signed document, the signer names and signing dates recorded by DocuSign, and the envelope identifier so you can trace the record back to its source. The original signed file is kept unchanged. Quillon does not alter signatures or certificates of completion.

## Who can use it

Only users with the administrator role can connect a DocuSign account or start an import. Contract owners and reviewers can view imported contracts according to the permissions set for their workspace, but they cannot change the connection. Your DocuSign account must have API access enabled, and the user who authorizes the connection must have permission to read completed envelopes in that account.

## Setup steps

1. Sign in to Quillon as an administrator and open Settings, then Integrations.
2. Select DocuSign and choose Connect account.
3. Sign in to your DocuSign account when prompted and review the permissions requested by Quillon.
4. Approve the connection. You will return to Quillon automatically.
5. Choose the date range for the import. The default is the full 5 years of completed envelopes.
6. Select the workspace or folder where imported contracts should be placed.
7. Start the import and keep the page open until the status shows as finished.
8. Review the summary of imported and skipped envelopes. Skipped items usually have a missing document or an unsupported format, and the reason is listed next to each one.

## Limits and things to know

- The import covers completed envelopes from the last 5 years only. Older envelopes must be uploaded manually.
- Very large envelopes may take longer to process, and the import status page shows progress.
- Attachments that DocuSign does not classify as part of the envelope are not brought in.
- The import is a one-time pass for the selected range. To bring in newer envelopes, run the import again with an updated date range, or contact your administrator to schedule a repeat import.
- Disconnecting DocuSign stops future imports but does not remove contracts already in your library.

## Troubleshooting

If the connection fails, confirm that your DocuSign account has API access and that the authorizing user has read permission for completed envelopes. If envelopes are missing, check the status filter and date range, since envelopes outside the 5 year window are not included. For any remaining issues, contact Quillon support with the envelope identifier and the time of the attempted import.
