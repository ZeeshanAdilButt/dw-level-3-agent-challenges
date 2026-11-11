---
title: Google Drive import
audience: public
owner_scope: everyone
authority: guide
version_chain: integ-gdrive
effective_from: '2026-07-01'
supersedes: null
links: []
type: integration
doc_id: doc-integ-gdrive
---

# Google Drive Import

## Overview

The Google Drive import connects your Quillon workspace to your Google Drive so that existing contract files can be brought into Quillon without manual uploads. Once imported, documents are indexed for search, can be assigned to obligation tracking, and can be linked to clauses in the clause library. The import reads files you select and places them in the matching workspace folder. It does not change or delete files in Google Drive.

## Who Can Use It

The Google Drive import is available to workspace administrators and to users who have been granted the contract import permission by an administrator. Users must have an active Google account with access to the Drive folders they intend to import. Quillon only reads files that the signed-in user is permitted to open in Google Drive, so the import never exposes documents to people who could not already see them.

## Supported File Types

The import accepts common contract formats, including PDF, Microsoft Word (DOCX), and plain text files. Google Docs are converted to DOCX during import. Scanned documents without a text layer are imported as images and will not be searchable until optical character recognition has been run on them.

## Limits

Google Drive import accepts files up to 100 MB each. Files larger than this limit are skipped and listed in the import summary so that they can be split or handled through a manual upload. Large batches are processed in the background, and you may receive a notification when a batch finishes. Shared drives and folders with very deep nesting may take longer to scan, and you can narrow the selection to speed up the process.

## Setup Steps

1. Sign in to Quillon as a workspace administrator.
2. Open Settings, then select Integrations, then select Google Drive.
3. Choose Connect and sign in with the Google account that will authorize access.
4. Review the permissions requested by Quillon and approve them. Quillon requests read access to the files you choose to import.
5. Select the folders or shared drives to include in the import.
6. Map each source folder to a destination folder in your Quillon workspace.
7. Review the file list and remove any files you do not want to import.
8. Start the import and wait for the summary to appear.
9. Check the import summary for skipped files, errors, and duplicates, then resolve any items that need attention.

## Handling Duplicates and Errors

If a file with the same name and content already exists in the destination folder, the import marks it as a duplicate and does not create a second copy. Files that fail to import, such as those that are password protected or corrupted, appear in the summary with a reason. You can correct the source file in Google Drive and run the import again for only those items.

## Disconnecting the Integration

To disconnect, open Settings, select Integrations, select Google Drive, and choose Disconnect. Disconnecting stops future imports but does not remove documents that were already imported. You can revoke Quillon's access at any time from your Google account security settings.

## Support

Questions about the Google Drive import can be directed to the Quillon support team through the in-app help menu. Include the import summary reference when you contact support so the team can trace the batch quickly.
