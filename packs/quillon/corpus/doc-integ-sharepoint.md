---
title: SharePoint connector
audience: public
owner_scope: everyone
authority: guide
version_chain: integ-sharepoint
effective_from: '2026-07-01'
supersedes: null
links: []
type: integration
doc_id: doc-integ-sharepoint
---

# SharePoint connector

## Overview

The Quillon SharePoint connector links a Microsoft SharePoint document library to your Quillon workspace so that contracts stored in SharePoint appear in Quillon search, obligation tracking, and renewal alerts. The connector syncs every 30 minutes, so new or updated files in the linked library reach Quillon within that window. The connector is a one-way read from SharePoint into Quillon for indexing, with optional write-back of signed final versions as described below.

## Who can use it

The connector is available to workspace administrators and to users with the Integrations permission. Users who only draft, review, or sign contracts in Quillon do not need the permission to benefit from synced documents. Your organization must hold a Microsoft 365 account with access to the SharePoint site you intend to link, and that account must have at least read access to the target library.

## What the connector does

Once connected, the connector performs four functions:

- It indexes the text and metadata of documents in the linked library, so they are searchable alongside contracts created inside Quillon.
- It extracts dates, parties, and obligations from synced agreements, which feed obligation tracking and renewal alerts.
- It records each synced document's SharePoint location so you can open the original file from Quillon.
- It optionally writes executed copies back to a designated folder in SharePoint once an e-signature workflow completes.

The connector does not modify, move, or delete existing files in your SharePoint library.

## Setup steps

1. Sign in to Quillon as a workspace administrator and open Settings, then Integrations.
2. Select SharePoint and choose Connect. You will be redirected to Microsoft to sign in.
3. Approve the requested permissions. Quillon requests read access to the selected site and write access only to the return folder if you enable write-back.
4. Select the SharePoint site and the document library to sync. You may link more than one library, but each library needs its own entry.
5. Choose whether to enable write-back. If you enable it, select the destination folder for executed copies.
6. Map any SharePoint columns you want to use as Quillon metadata, such as business unit, counterparty, or owner.
7. Select Start initial sync. The first sync may take longer than subsequent syncs, depending on library size.
8. Confirm the connection status shows Active and that a sample document appears in search.

## Limits and considerations

- Sync frequency is fixed at every 30 minutes and cannot be shortened by workspace settings.
- Files larger than the size limit shown in the connector settings page are indexed by name and metadata only.
- Password-protected files and files with restricted sensitivity labels may not be readable by the connector. Such files are listed in the connection report.
- Deleting a file in SharePoint removes it from Quillon search at the next sync, but Quillon retains the record of any obligation already created from it.
- Version history in SharePoint is not imported. Quillon indexes the current version of each file.
- Each workspace may connect a limited number of libraries. Check the connector settings page for the current number.

## Troubleshooting

If the status shows Error, confirm that the Microsoft account used for setup still has access to the library and that its credentials have not expired. Reconnect the connector from Settings, then Integrations, then SharePoint, and select Reauthorize. For documents that do not appear, check the connection report for skipped files and their reasons.
