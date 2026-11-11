---
title: Use merge fields in templates
audience: public
owner_scope: everyone
authority: guide
version_chain: sup-template-fields
effective_from: '2026-07-15'
supersedes: null
links: []
type: support
doc_id: doc-sup-template-fields
---

# Use merge fields in templates

Merge fields let you fill a contract template with details from your records, so each document is generated correctly without retyping. This guide explains how to insert and complete merge fields in Quillon.

Merge fields are written in double curly braces, for example {{counterparty_name}}. When a contract is generated, Quillon replaces each field with the value stored for that contract.

## Before you begin

Make sure you have edit access to the template and that the data you need, such as the counterparty record, is already entered in Quillon.

## Steps

1. Open the template you want to edit from the Templates library.
2. Place your cursor where the value should appear, for example in the opening paragraph after "This agreement is made with".
3. Select Insert field, then choose the field from the list. Alternatively, type the field name inside double curly braces, such as {{counterparty_name}}.
4. Repeat for each value the template needs, such as the effective date or the contract owner.
5. Select Preview to generate a sample document and confirm each field shows the expected value.
6. If a field shows as blank or as the raw code, check that the source record contains that value, then correct the field name or the record.
7. Save the template and submit it for approval if your workspace requires it.

## Tip

Preview the template with a real record before publishing it to your team. Fields that look correct in the editor can behave differently once the source data is filled in.
