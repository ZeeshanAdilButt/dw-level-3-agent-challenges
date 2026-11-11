---
title: Search tips and operators
audience: public
owner_scope: everyone
authority: guide
version_chain: sup-search-tips
effective_from: '2026-07-15'
supersedes: null
links:
- doc-prod-search
type: support
doc_id: doc-sup-search-tips
---

# Search tips and operators

## How Quillon indexes your contracts

Quillon builds a search index across every contract stored in your workspace. When a document is uploaded, drafted from a template, or signed through the e-signature workflow, the platform extracts its text, reads its structure, and adds it to the index. Clauses, headings, party names, dates, and defined terms are all captured so that a search can reach into the body of an agreement rather than matching only on file names or folder labels.

The index covers the full lifecycle of a contract. A draft that is still moving through review is searchable alongside the final executed copy, and superseded versions remain findable under their version history. This matters for teams that need to answer questions such as "which vendor agreements still contain the old liability wording" or "where did we first agree to a particular carve-out." Because the index reflects the text as it stood at each saved version, a search can show you when a phrase first appeared and when it was removed.

Indexing runs as documents change. Once a contract is saved or signed, its text is queued for indexing and becomes searchable shortly afterward. Very large uploads, such as scanned bundles with many pages of poor image quality, may take longer to appear in results than typed documents. If a document you expect is not yet showing up, check its status in the document panel before assuming it is missing.

Search respects the permissions set on each workspace, folder, and matter. You will only see results for contracts you are authorized to open. Administrators can see a wider set of results, and they can review access settings in the workspace administration area. A result that appears in your list is one you can open, so there is no need to worry that the search itself will expose restricted material to people who should not see it.

The index also understands the structure of common contract types. Recitals, definitions, indemnity clauses, termination sections, and schedules are recognized as separate parts of a document. This allows you to narrow a search to a particular kind of clause when that is what you need, although the general text search described below works on any part of a contract.

## Basic searches

The simplest search is a list of words. Type the terms you want to find, separated by spaces, and Quillon returns contracts that contain all of them somewhere in their text. Results are ranked by how closely the matching words appear to one another and by how recently the document was updated. Common words such as "the," "and," and "of" are ignored unless they are part of an exact phrase.

Plain word searches are forgiving. Quillon matches different forms of the same word, so a search for "terminate" will also surface documents that say "terminated" or "termination." Capitalization is ignored. This makes simple searches a good starting point when you are not sure of the exact wording used in a particular agreement.

When you want to limit results to a single meaning or a specific wording, move to the operators described in the sections that follow. Operators give you control over how words are matched, which is especially useful in contracts, where a difference of a single word can change the obligations under a clause.

Search results show a short excerpt around the matching text. Use the excerpt to judge whether a document is relevant before opening it. If several results look similar, the date and matter fields shown beside each result can help you find the right version quickly.

## Searching for exact phrases

Many contract questions depend on precise wording. A clause that says "reasonable efforts" carries a different meaning from one that says "commercially reasonable efforts," and a search for the two words in any order will not tell you which one a particular agreement uses. To find the exact wording, wrap the words in double quotes. For example, searching for "commercially reasonable efforts" returns only documents where those three words appear together, in that order, with no other words between them.

Exact phrase searches are the most reliable way to locate defined terms, standard clause headings, and statutory references. They are also useful for finding a specific sentence that you remember from a prior agreement. Quotation marks are matched exactly, so a phrase should be typed with the words spelled as they appear in the contract. If a phrase returns no results, try a shorter version of it, since punctuation and line breaks in the source document can sometimes separate words that look adjacent on screen.

Use quotes sparingly when you are unsure of the wording. A broad search with a few key terms often returns more useful results at the start of an investigation, and an exact phrase search can then confirm the precise language once you have identified a likely document.

Exact phrase searches can be combined with other terms. For instance, you can search for a quoted clause heading together with a counterparty name to narrow the results to agreements with that party. The combined search will return only documents that satisfy both conditions.

## Proximity searches with NEAR

Sometimes you know two words appear in the same clause but not that they appear as a phrase. A contract might discuss "assignment" and "consent" in the same paragraph without using the words side by side. The NEAR operator handles this situation. It finds two words that appear within a set distance of each other in the document text.

The NEAR operator finds two words within 10 words of each other. Place the operator between the two terms, for example "assignment NEAR consent," and Quillon returns documents where the two words fall within that distance, regardless of which word comes first. The window of 10 words is measured across the document text, so a search for "indemnify NEAR cap" will surface an indemnity clause where a liability cap is described nearby, even if the cap is written in a separate sentence.

Proximity searches are most useful for locating clauses that cover the same subject using varied language. Because the distance is limited, the results tend to concern the same paragraph or provision rather than unrelated parts of a long agreement. If results are too broad, try putting more specific terms on either side of the operator. If results are too narrow, consider a plainer pair of words that is more likely to appear close together.

The NEAR operator works with exact phrases as well. A search can compare a quoted phrase with a single word, which lets you check whether a specific clause title is discussed near a particular concept. Keep in mind that the distance is counted in words, so punctuation and short connecting words still count toward the total.

## Operator reference

The table below summarizes the search operators described in this guide and how each one is typed.

| Operator | How to type it | What it finds |
|---|---|---|
| Plain terms | Words separated by spaces | Documents containing all the words, in any order |
| Exact phrase | Words wrapped in double quotes | The words together, in the same order |
| Proximity | Two terms joined by NEAR | Both terms within 10 words of each other |

## Tips for better results

Start broad and narrow down. A short first search helps you see how the wording varies across your contracts, and you can add operators once you know the terms in use. If a search returns too many results, add a second term or an exact phrase. If it returns none, check spelling, try a synonym, or remove quotes to see whether a near match exists.

Use the filters alongside your search. Filters for matter, counterparty, document type, and date help you focus results on the agreements that matter for your question. Combining a filter with a proximity search is often the fastest way to find a clause in a large portfolio of similar contracts.

Save searches you run often. Saved searches can be shared with colleagues in the same workspace, which keeps teams working from the same set of results when reviewing renewals or preparing for an audit.

If you believe a document that should appear in results is missing, confirm that it has been saved or signed and that you have access to its folder. Document status and permissions are the most common reasons a contract does not appear. Your workspace administrator can help if access needs to be adjusted.
