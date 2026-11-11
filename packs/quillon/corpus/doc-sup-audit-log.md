---
title: Read and export the audit log
audience: public
owner_scope: everyone
authority: guide
version_chain: sup-audit-log
effective_from: '2026-07-15'
supersedes: null
links:
- doc-sup-retention
type: support
doc_id: doc-sup-audit-log
---

# Read and export the audit log

## Purpose of this guide

The audit log in Quillon records significant actions taken on contracts, templates, clauses, approvals, signatures, obligations, and user accounts within your workspace. Administrators, legal operations staff, and finance team leads use it to answer questions such as who changed a clause, when a contract was sent for signature, who approved a renewal, and which user exported a set of documents. This guide explains how to find the information you need, how to narrow the results with filters, how to understand the event types you will see, and how to export the log for review outside the product.

Reading the audit log does not change any contract or setting. Viewing and exporting entries is safe to do at any time, although access to the log depends on your role. Workspace owners and administrators can view the full log for the workspace. Other roles may see only events related to contracts they are permitted to access. If you expect to see an event and cannot find it, check your role permissions first, then review the filters described below.

## Opening the audit log

To open the audit log, sign in to Quillon and select Administration from the main navigation menu. Choose Audit log from the list of administration pages. The page loads the most recent events first, with the newest entry at the top of the list. Each row shows the date and time of the event, the user or system process that performed the action, the event type, the object the event affected, and a short description of the change.

Times are shown in the time zone set for your workspace. If you work with colleagues in other regions, confirm the workspace time zone under Administration settings before comparing entries against records kept elsewhere. Timestamps in exports follow the same setting, so a note in your review file should record the zone used.

Select any row to open the event detail panel. The panel shows the full description, the identifier of the affected object, the IP address recorded for the session where available, and, for changes to text, a comparison of the previous and new values. Use the panel to confirm details before you draw conclusions from a summary row.

## Filtering the results

The filter bar sits above the event list. Filters combine with one another, so each added filter narrows the results further. Clear all filters at any time using the Reset control at the right end of the bar.

1. Date range. Set a start date and an end date to limit results to a period. Leaving the end date empty returns events up to the present.
2. User. Choose one or more users from the directory to show only events they performed. System processes, such as scheduled renewal alerts, appear under their system name and can be selected in the same way.
3. Event type. Choose one or more event types from the list described in the next section.
4. Object type. Limit results to contracts, templates, clauses, approval requests, signature envelopes, obligations, or user accounts.
5. Object identifier. Enter the identifier of a specific contract, template, or envelope to see its complete history.
6. Keyword. Enter a word or phrase to search within event descriptions. Keyword search matches descriptions only and does not search the contents of documents.

When you apply a filter, the results count updates at the top of the list. If the count is zero, widen the date range first, since this is the filter most often set too narrowly.

## Understanding event types

Event types are grouped by the part of the product they relate to. Knowing the groups helps you choose the right filter quickly.

Drafting events record the creation of a contract from a template, edits to contract text, and the addition or removal of clauses from the clause library. Entries in this group show the author and the section that changed.

Approval events record requests for review, approvals, rejections, and reassignments. An approval entry names the approver and the decision, and a rejection entry includes the reason where one was entered.

Signature events record when a document is sent for electronic signature, viewed by a signer, signed, declined, or voided. Signature events carry the envelope identifier, which links them to the signed copy.

Obligation events record the creation, update, and completion of obligations such as payment dates, reporting duties, and notice periods that were tracked from a contract.

Renewal events record when a renewal alert was generated, sent, acknowledged, or dismissed, and when a renewal was recorded as taken up or not taken up.

Search and export events record when a user searched signed contracts in a way the product logs, and when an audit log export was created or downloaded. These entries exist so that access to sensitive material can be reviewed.

Administration events record changes to users, roles, workspace settings, and integrations.

## Exporting the audit log

Exports let you keep a copy of the log for records, share it with an auditor, or analyse it in a spreadsheet. The export uses the filters currently applied, so set your filters before you start. An export contains only the events that match them.

1. Apply the filters you need and confirm the results count.
2. Select Export at the top right of the event list.
3. Choose the file format offered for your workspace, and confirm the export.
4. Wait for the export to finish. Large exports may take a short time to prepare. A notification appears when the file is ready, and it is also listed under Exports on the same page.
5. Download the file from the Exports list. Downloads are available to the user who requested the export.

Each export holds up to 100,000 events. If your filtered results exceed this number, the export will include the first 100,000 events in the current sort order and will note that the result was truncated. To capture everything, split the work by date range. For example, export one quarter at a time, and confirm that the counts across the files add up to the total shown in the list for the full period.

Store exported files in a location with the same access controls you apply to other confidential records. The file contains user names, object identifiers, and change descriptions, and it should be treated accordingly.

## Checking an export

Before relying on an export, compare the number of rows in the file with the results count shown in Quillon for the same filters. Check that the first and last timestamps fall within the date range you set. If the export was truncated, confirm that you have exported the remaining periods. Record the date you ran the export, the filters applied, and the name of the person who ran it, so that the export can be reproduced later.

## Getting help

If an entry looks incorrect, if you cannot see events you expect, or if an export fails, contact your workspace administrator first. Administrators can confirm role permissions and check whether an export request completed. If the problem continues, contact Quillon support through the Help menu and include the filters used, the time of the event in question, and the identifier of the affected object where you have it.
