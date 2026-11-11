---
title: Box import
audience: public
owner_scope: everyone
authority: guide
version_chain: integ-box
effective_from: '2026-07-01'
supersedes: null
links: []
type: integration
doc_id: doc-integ-box
---

# Box Import

## Overview

The Box import integration lets your team bring contracts stored in Box into Quillon so they can be searched, tracked, and managed alongside everything else in your contract library. Once imported, documents keep their original file content, and Quillon adds metadata such as parties, dates, and obligations where it can identify them. Box import accepts files up to 250 MB each, so most standard contract packages, scanned agreements, and exhibit bundles fit within that limit.

## Who Can Use This Integration

Box import is available to Quillon administrators and to users who hold permission to manage repositories in their workspace. Individual team members can import files they have access to in Box, but only administrators can connect the Box account to the workspace and set the folders that Quillon is allowed to read. Your Box administrator must also approve the connection from the Box side, so coordinate with that team before you begin.

## Before You Start

Confirm the following before you connect:

- You have administrator rights in your Quillon workspace.
- You have an active Box account with access to the folders holding your contracts.
- Your Box administrator has allowed third-party applications to connect to your Box tenant.
- You have identified which folders contain contracts you want to import, and you have removed any drafts or personal files you do not want in the library.

## Setup Steps

1. Sign in to Quillon and open Settings, then select Integrations.
2. Choose Box from the list of available connectors and select Connect.
3. Sign in to your Box account when prompted and review the permissions Quillon requests. Quillon asks only for read access to the folders you select.
4. Approve the connection. Your Box administrator may need to confirm the request at this stage.
5. Select the folders you want Quillon to import. You can add or remove folders later.
6. Choose how new files should be handled: import them automatically on a schedule, or import only when you start a manual sync.
7. Run a first import for one folder and review the results in the contract library before importing the rest.
8. Assign default owners or tags to the imported contracts if your team uses them for routing and approvals.

## Import Limits and Behavior

Each file must be 250 MB or smaller. Files larger than that limit are skipped and listed in the import report so you can split them or upload them directly. Supported file types match the document formats Quillon already reads for search and obligation tracking. Files that cannot be read, such as password-protected documents, are flagged for review rather than imported silently.

Imports do not delete or change anything in Box. If a file is moved or renamed in Box, Quillon updates its record on the next sync. If a file is deleted in Box, Quillon keeps the last imported version in the library so your records remain intact, and marks it as removed at source.

## Troubleshooting

If a folder does not appear in the picker, check that your Box account can open it and that your Box administrator has not restricted it. If a file is missing after an import, open the import report and look for the file name, which will show whether the file was skipped for size, type, or readability. For connection errors, disconnect Box from the Integrations page and connect again, which refreshes the authorization.
