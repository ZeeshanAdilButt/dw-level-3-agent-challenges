---
title: Retention and audit log settings
audience: public
owner_scope: everyone
authority: guide
version_chain: sup-retention
effective_from: '2026-07-15'
supersedes: null
links: []
type: support
doc_id: doc-sup-retention
---

# Retention and audit log settings

## Overview

This guide explains how Quillon keeps audit logs and deleted contracts, how each plan differs, and how administrators can review and adjust these settings. It applies to all customers using the contract-management platform, including law firms and corporate finance teams. Read it alongside your organization's records policy, since your legal or compliance team may require longer periods than the defaults described here.

## Retention periods by plan

The table below summarizes how long audit logs are kept for each plan. Audit logs record who viewed, edited, approved, signed, or exported a contract, along with the time of each action.

| Plan | Audit log retention |
|---|---|
| Starter | 3 months |
| Team | 6 months |
| Pro | 13 months |
| Enterprise | 36 months |

Retention periods begin on the date an event is recorded. Once the period ends, the event is removed from the audit log automatically during the next nightly cleanup. Removal is permanent, so administrators who need a longer record should export logs before they expire. Exports are available from the Audit section of the administration console in CSV format.

## How audit log retention works

Audit logs are separate from contract content. Expiry of an audit log entry does not change or delete the contract it refers to. It only removes the record of the action. Each entry stores the user identifier, action type, contract identifier, and timestamp. Entries are kept in the same region as the workspace that created them.

Administrators can filter logs by user, contract, action type, and date range before exporting. Filters apply to the export only and do not change what is retained. If your plan's retention period is shorter than your internal requirement, schedule regular exports to an archive you control.

Changing plans affects future retention. If you move from a plan with a shorter period to one with a longer period, earlier events that are still within the shorter window remain available, and the longer period applies to new events from the date of the change. Moving to a plan with a shorter period does not shorten the retention of events already recorded under the earlier plan, but those events will expire under the new plan's rule when they reach the new limit. Confirm with your account representative before changing plans if audit history is critical to a pending matter.

## Legal holds

A legal hold pauses the automatic removal of audit logs and contract records for a defined set of contracts or users. Holds are intended for situations such as active litigation, regulatory inquiries, internal investigations, or preservation requests received from outside counsel. While a hold is active, the affected records are excluded from the nightly cleanup and from any scheduled deletion, regardless of plan retention periods.

Only administrators with the legal hold permission can create, modify, or release a hold. Each hold requires a name, a description, and the scope of records it covers. Scope can be a single contract, a folder, a set of tags, or all records associated with a named user. The platform records who created the hold, when it was created, and when it was released.

Releasing a hold returns affected records to normal retention rules. Records whose retention period has already passed during the hold will be removed at the next cleanup, so releasing a hold should be coordinated with the people responsible for the matter. Quillon does not provide legal advice about whether a hold is required. Your legal team decides the scope and duration.

## Automatic archiving

Contracts that have reached an end state, such as expired, terminated, or fully performed, can be moved to archive automatically after a period set by the workspace administrator. Archived contracts remain searchable and can be restored to active status at any time. Archiving does not affect audit logs. The events that occurred while a contract was active remain in the log for the period set by your plan.

Archive rules can be set by contract type, owner, or status. Rules are evaluated once per day. Administrators can preview which contracts a rule would affect before enabling it. Archived contracts count toward storage limits in the same way as active contracts, so archive rules do not reduce storage use on their own.

Archived contracts are not deleted automatically. Deletion is a separate action that requires an administrator to confirm, or a user with delete permission to request, followed by the recycle bin process described below.

## Deleted contracts and the recycle bin

When a contract is deleted, it moves to the recycle bin rather than being removed immediately. Deleted contracts stay in the recycle bin for 30 days, after which they are permanently removed. During that period, an administrator can restore a deleted contract with its full history, attachments, and signatures intact. Restored contracts return to the folder they came from, or to the root folder if that folder no longer exists.

Contracts under an active legal hold are not permanently removed from the recycle bin, even after the 30-day period has passed, until the hold is released. Permanent removal from the recycle bin cannot be reversed. Quillon does not keep backup copies of permanently removed contracts beyond the standard backup cycle managed by the platform, so customers who need a longer recovery window should export contracts before deleting them.

## Recommendations

Review your retention settings each quarter. Confirm that your audit log period meets your internal and regulatory requirements, schedule exports where it does not, and make sure legal holds are created early whenever a matter is anticipated. Keep a record of who is authorized to create and release holds, and train administrators on the recycle bin so that deletions are intentional. For questions about a specific plan or a retention requirement, contact your account representative.
