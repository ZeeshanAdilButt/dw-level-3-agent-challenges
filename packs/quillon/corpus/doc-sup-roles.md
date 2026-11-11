---
title: Roles and permissions
audience: public
owner_scope: everyone
authority: guide
version_chain: sup-roles
effective_from: '2026-07-15'
supersedes: null
links: []
type: support
doc_id: doc-sup-roles
---

# Roles and permissions

## Purpose and scope

This guide explains how access works in Quillon, the contract-management platform used by law firms and corporate finance teams. It applies to every workspace from the effective date of 2026-07-15. Use it to decide which people should hold which role and what each role can do across drafting, approvals, e-signature, obligation tracking, renewal alerts and search.

## Built-in roles

Quillon has four built-in roles: Admin, Manager, Editor and Viewer. Each user in a workspace holds exactly one of these roles at a time. Roles are assigned per user and can be changed by an Admin at any time. The four roles are cumulative in a simple sense: each role keeps the abilities of the roles below it, with a few exceptions noted in the table.

## Role-by-action table

The table below shows which role can perform each common action. "Yes" means the action is allowed, and "No" means it is not.

| Action | Admin | Manager | Editor | Viewer |
|---|---|---|---|---|
| Change billing details | Yes | No | No | No |
| Invite and remove users | Yes | Yes | No | No |
| Assign roles to users | Yes | No | No | No |
| Create contracts from templates | Yes | Yes | Yes | No |
| Edit clause library entries | Yes | Yes | No | No |
| Approve or reject a contract | Yes | Yes | No | No |
| Send for e-signature | Yes | Yes | Yes | No |
| Set obligation and renewal alerts | Yes | Yes | Yes | No |
| Search across signed contracts | Yes | Yes | Yes | Yes |
| View signed contracts | Yes | Yes | Yes | Yes |
| Download signed originals | Yes | Yes | Yes | No |

## Notes on the table

Only Admins can change billing details. This includes payment method, billing contact and invoice recipients. Other roles may see that a plan is active but cannot alter the commercial terms.

Viewers cannot download signed originals. They can search, open and read signed contracts inside Quillon, which supports reference use without granting copies outside the platform. If a Viewer needs an original, an Editor or Manager should provide it through the workspace's approved channel.

Managers hold the approval and clause library responsibilities that Editors do not. Keeping approvals with Managers helps separate drafting work from sign-off.

## Recommended practice

Assign the Admin role to as few people as practical, ideally those responsible for the workspace's configuration and billing. Give Editors the access needed for day-to-day drafting and sending, and use Viewers for colleagues who only need to consult executed agreements. Review role assignments on a regular schedule and remove access promptly when someone leaves the team or changes responsibilities.

## Getting help

If a permission seems wrong for your work, contact your workspace Admin first. The Admin can review your assigned role and adjust it. Quillon support can help with questions about how a role behaves but cannot change role assignments on a customer's behalf.
