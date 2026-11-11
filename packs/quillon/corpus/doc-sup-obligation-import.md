---
title: Import obligations from a spreadsheet
audience: public
owner_scope: everyone
authority: guide
version_chain: sup-obligation-import
effective_from: '2026-07-15'
supersedes: null
links: []
type: support
doc_id: doc-sup-obligation-import
---

# Import obligations from a spreadsheet

This guide explains how to bring contract obligations into Quillon from a CSV file. Use it when you already track obligations in a spreadsheet and want them to appear alongside your signed contracts, with due dates and owners attached.

## Before you start

Confirm that each row in your file describes one obligation. A CSV obligation import accepts up to 2,000 rows, so split larger files into batches. Make sure the contract each obligation belongs to already exists in Quillon, because obligations are matched to contracts by contract ID.

## Steps

1. Open the Obligations area from the main navigation and select Import.
2. Download the CSV template so your column headers match exactly.
3. Fill in one row per obligation, including the contract ID, obligation description, owner email, and due date.
4. Save the file as CSV (comma-delimited) with UTF-8 encoding.
5. Select Upload and choose your file. Quillon checks the file before importing anything.
6. Review the preview screen. Rows with errors are flagged with the reason, such as an unknown contract ID or a missing owner.
7. Correct flagged rows in your spreadsheet and upload the file again, or choose Skip flagged rows to import only the valid ones.
8. Select Confirm import. You will receive a summary showing how many obligations were created.
9. Open a contract to check that its obligations appear with the correct owners and due dates.

## Tip

Run a small test import with five to ten rows first. This shows you any column or format issues before you load the full file.
