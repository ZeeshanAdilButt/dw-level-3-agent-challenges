---
title: Bulk import existing contracts
audience: public
owner_scope: everyone
authority: guide
version_chain: sup-bulk-import
effective_from: '2026-07-15'
supersedes: null
links: []
type: support
doc_id: doc-sup-bulk-import
---

# Bulk import existing contracts

## Purpose and scope

This guide explains how to move a backlog of existing contracts into Quillon so that they become searchable, trackable, and ready for renewal alerts and obligation tracking. It is written for administrators and records staff at law firms and corporate finance teams who are setting up a new workspace or consolidating contracts from shared drives, email archives, and older contract systems.

Bulk import is a support function for migrating existing paper and digital records. It does not replace the drafting, approval, or e-signature workflows used for new agreements. Once imported, contracts can be searched, linked to obligations, and monitored for renewal dates, but Quillon does not interpret the legal meaning of imported terms. Your reviewing lawyers or finance staff remain responsible for confirming key dates, parties, and obligations after import.

Read this guide in full before starting your first batch. The preparation steps in the next sections prevent most of the problems that teams encounter, including rejected files, mismatched metadata, and missing renewal alerts.

## Planning the migration

Before you upload anything, decide what you are migrating and in what order. A useful first step is to list every location where contracts currently live, such as network folders, document management systems, cloud drives, email attachments, and physical scans held by records teams. For each location, note roughly how many files it holds and whether they are finished, signed copies or working drafts.

Separate signed agreements from drafts and superseded versions. Signed and executed contracts should form the core of your first import, since they carry the obligations and renewal dates that the platform tracks. Drafts can be imported later into a separate folder or left in their original location, unless your matter workflows depend on them. Superseded versions of the same agreement are best kept only where they are needed for audit history, because importing every version inflates search results and makes it harder to identify the operative document.

Agree on ownership before the import starts. Assign one person to approve the final batch, one or two people to check metadata on a sample of records, and a named contact for questions from the matter or deal teams. Clear responsibility at this stage reduces rework later.

Consider the sequence of batches. Many teams start with a pilot batch of a few hundred files from a single practice group or business unit. The pilot shows how file names, folders, and dates come through, and it gives reviewers a manageable set to check. Larger batches follow once the pilot results are acceptable.

## Limits for a bulk import batch

Each bulk import batch can hold up to 10,000 files, and each individual file in the batch can be up to 100 MB. If a source folder holds more than 10,000 files, divide it into several batches. If a single scanned bundle exceeds 100 MB, split it into smaller parts at logical boundaries, such as by agreement, schedule, or year, before upload. Keep a note of how you split any file so that the parts can be reassembled in the search results.

Batch sizes should also reflect how much time your reviewers have. A batch that is technically within the limit but too large to check will cause problems if errors go unnoticed. Many administrators find it practical to keep batches smaller than the maximum so that metadata review remains realistic.

Supported file types are standard document and image formats commonly used for contracts. Scanned paper contracts should be converted to searchable PDF where possible, because text recognition improves search results across the signed contract library. Files that are password-protected or locked for editing may need to be unlocked by their owners before import.

## Preparing folders and file names

Consistent folder and file naming makes the import easier to check and makes the imported library easier to navigate. Quillon reads folder structure and file names as hints when it creates records, so a clear convention pays off after migration.

A practical folder structure separates contracts by client, business unit, or counterparty, then by year or contract type. For example, a finance team might organise folders first by supplier and then by agreement type, while a law firm might organise by matter number. Choose one structure and apply it across the whole batch.

File names should identify the counterparty, the agreement type, and the effective date in a consistent pattern. A pattern such as counterparty, underscore, agreement type, underscore, date in year, month, day order works well and sorts correctly. Avoid special characters that may cause problems in some systems, and avoid putting key information only inside the file body, because the import relies on names to produce readable records.

Remove or rename obvious duplicates before upload where you can. Files named "final", "final2", and "final_really" are hard to distinguish later. Renaming them with their signing dates saves time during review. Note, however, that the platform handles true duplicates separately, as described in the final section of this guide.

Keep a simple index or spreadsheet that lists each folder, its owner, and the expected number of files. Comparing the expected count with the number of records created after import is a fast way to spot missing files.

## Metadata to check after import

After each batch completes, a reviewer should check a sample of records against the source documents. Focus on the fields that drive day-to-day use: counterparty name, agreement type, effective date, expiry or renewal date, notice periods, and the owning business unit or matter. Errors in these fields affect search, renewal alerts, and obligation tracking, so they matter more than cosmetic issues in titles.

Pay particular attention to renewal dates and notice periods. An agreement that auto-renews needs an accurate renewal date and an accurate notice period so that alerts arrive in time for the team to act. If a contract's dates cannot be read clearly from the document, mark it for manual correction rather than accepting a guessed value.

Check that counterparties are recorded under consistent names. The same supplier may appear under several spellings across old contracts, and inconsistent names fragment search results. Standardising counterparty names during review is worth the effort.

Record the reviewer's name and the date of review in your own tracking index. This creates an audit trail showing who confirmed each batch and when.

## Running the import

Start the import from the bulk import area of the administration console. Select the batch folder, confirm the file count, and review the preview if one is shown. The preview lists the files that will be imported and any that the system cannot process. Resolve unsupported files before confirming, either by converting them or by excluding them and recording the exclusions.

Once you confirm, the batch runs in the background. You can continue using the workspace while it completes. Do not start a second batch from the same source folder until the first has finished, because overlapping batches make it harder to track which records came from which upload.

When the batch completes, review the summary. It reports the number of files received, the number imported, the number skipped as duplicates, and the number that could not be processed. Compare these figures with your index. Any unexplained gap should be investigated before the next batch begins.

## Duplicate detection by checksum

Bulk import detects duplicate files by checksum and skips them. A checksum is a fingerprint calculated from the exact contents of a file. Two files with identical contents produce the same checksum, even if they have different names or live in different folders. When the import encounters a file whose checksum matches one already in the library, it skips the new copy and records it in the batch summary.

This behaviour is useful because the same signed agreement often appears in several places, such as a shared drive, a finance folder, and an email attachment. Importing it once keeps the library clean and avoids duplicate renewal alerts.

Checksum matching only catches byte-for-byte identical files. A scanned copy of a contract and a digitally generated PDF of the same agreement will have different checksums, even though the text is the same, so both will be imported. Likewise, a file that has been re-saved, re-printed to PDF, or had its metadata changed will not match. Reviewers should watch for these near-duplicates during the sample check and decide which copy is the operative version. Where a near-duplicate is found, you can link the records or archive the less authoritative copy after import.

Skipped duplicates are listed in the batch summary so that you can confirm that the kept copy is the one you intended. If the summary shows that the wrong version was kept, check which copy was uploaded first and adjust the source folders before re-running the affected batch.

Because duplicate detection depends on checksums, editing a file before upload changes its checksum and may cause the same agreement to be imported twice. Finalise the source files before you begin, and avoid annotating originals in place during the migration window.
