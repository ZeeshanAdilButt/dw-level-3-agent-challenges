---
title: Provision users with SCIM
audience: public
owner_scope: everyone
authority: guide
version_chain: sup-scim
effective_from: '2026-07-15'
supersedes: null
links:
- doc-plan-enterprise
type: support
doc_id: doc-sup-scim
---

# Provision users with SCIM

## Purpose and scope

This guide explains how administrators can provision and deprovision users in a Quillon workspace automatically from an identity provider using the System for Cross-domain Identity Management (SCIM) standard. Automated provisioning keeps the list of people who can sign in, draft, approve, and search contracts aligned with your company directory, so that joiners receive access on their first day and leavers lose access when their directory account is disabled. This article is written for workspace owners and identity administrators who manage the connection between their identity provider and Quillon.

SCIM provisioning is available on the Enterprise plan only. Workspaces on other plans will not see the SCIM settings described below. If you are unsure which plan your workspace uses, check the Billing page in workspace settings before you begin, or contact your Quillon account team.

Before you start, confirm that you have the following: owner or administrator rights in the Quillon workspace, administrative access to your identity provider, a list of the groups you want to map to Quillon roles, and a decision on which user attributes must be present for an account to be created. Plan a short test with two or three test accounts before you enable provisioning for the whole company.

## How the connection works

Quillon exposes a SCIM endpoint for your workspace. Your identity provider calls that endpoint to create, update, and deactivate user records, and to push group membership changes. Authentication is handled by a bearer token that you generate inside Quillon and paste into your identity provider. The identity provider remains the source of truth: changes made in Quillon to a provisioned user's profile fields, such as name or email, may be overwritten at the next sync, so make those changes in the directory instead.

Provisioning is one-way from the identity provider to Quillon. Single sign-on settings are configured separately and are not replaced by SCIM. Many organisations configure both, using single sign-on for authentication and SCIM for lifecycle management.

## Set up the SCIM token

Follow these steps in order.

1. Sign in to Quillon as a workspace owner and open Settings, then Identity, then Provisioning.
2. Select Create SCIM token and give it a descriptive name that identifies the identity provider and the environment, for example "Corporate directory production."
3. Copy the token and the SCIM base URL shown on the screen. Quillon shows the token only once. Store it in your identity provider's secret store immediately.
4. Note the expiry date displayed next to the token. SCIM tokens expire after 12 months from the date of creation, and a token that has expired will cause all provisioning calls to fail without warning in the directory's own logs. Put a reminder in your calendar well before the expiry date.
5. Rotate the token before it expires by creating a new one, updating the secret in your identity provider, confirming a successful test sync, and then revoking the old token.

Keep tokens scoped to a single workspace and a single identity provider. If you run more than one directory, for example a corporate directory and a separate contractor directory, create a separate token for each so that you can revoke one without affecting the other.

## Configure the identity provider

Most identity providers include a Quillon application template or a generic SCIM application type. Choose the template where available, because it pre-fills the attribute names. Enter the SCIM base URL and the token you copied in the previous section, then use the connection test built into your identity provider. A successful test returns a confirmation that the endpoint responded and that the token was accepted.

Select the provisioning actions you want: create users, update user attributes, and deactivate users. Enable group push if you intend to map groups to Quillon roles. Set the sync frequency according to your organisation's policy. Changes made in the directory are usually pushed within minutes, but some identity providers run scheduled cycles, so allow time for the first full sync.

Assign only the users and groups that should have access. Assigning an application to a broad group will provision every member of that group, including people who do not need Quillon.

## Map attributes

Attribute mapping tells Quillon which directory fields correspond to its user fields. The table below lists the minimum mapping. Your identity provider template may provide defaults, but verify each row.

1. Map the directory's unique username or user principal name to the Quillon username field. This value must be unique across the workspace and should not change over the life of the account.
2. Map the directory's primary work email to the Quillon email field. Quillon uses this address for notifications, approval requests, and e-signature invitations, so it must be accurate and current.
3. Map given name and family name to the corresponding Quillon fields. These appear in contract activity histories, so consistent formatting matters for audit purposes.
4. Map the department or cost centre attribute to the Quillon department field if you use department-based permissions or reporting.
5. Map the manager attribute if you want approval routing to follow the reporting line. Approval rules in Quillon can reference the manager field, and a missing value will cause those rules to fall back to the workspace default approver.
6. Map the active flag to the Quillon account status so that deactivating a directory account immediately suspends the Quillon account.

Do not map fields that change frequently and have no business meaning in Quillon, such as office location or phone extension, unless a specific workflow depends on them. Fewer mapped fields mean fewer possible conflicts.

## Map groups to roles

Group push allows Quillon to assign roles based on directory group membership. Create one directory group per Quillon role you need, for example "Contracts Editors" for users who draft and submit, "Legal Approvers" for users who approve, and "Workspace Administrators" for users who manage settings. Push these groups to Quillon through the identity provider's group provisioning settings.

When a user is added to a group, Quillon assigns the mapped role at the next sync. When the user is removed, the role is withdrawn. A user who belongs to no mapped group receives the default viewer role, which allows searching signed contracts but not drafting or approving. Review the default role with your legal and records teams before you go live, because it determines what newly provisioned staff can see.

## Test before rollout

Run a pilot with a small group of users who represent the main roles in your organisation. For each test account, confirm the following: the account is created with the correct name and email, the correct role is assigned, the user can sign in through single sign-on if that is configured, the user can see only the contracts and templates their role allows, and deactivating the account in the directory suspends access in Quillon within the expected time.

Keep a record of the test results. Auditors and information security reviewers frequently ask how provisioning was validated.

## Troubleshooting

Most provisioning problems fall into three categories: authentication failures, attribute mismatches, and duplicate accounts.

If every call fails, check the token first. Confirm that it has not expired and that it was pasted completely, without leading or trailing spaces. Confirm that the base URL matches the one shown in Quillon. If the token is valid but calls still fail, check that the Enterprise plan is active on the workspace, since SCIM endpoints are not enabled on other plans.

If a specific user fails, open the failed record in your identity provider's provisioning log. Look for a missing or malformed email address, a username that is already in use, or a required attribute left blank.

If the log shows ERR-SCIM-409, the request was rejected because a user with the same email address already exists in the workspace. This usually happens when someone was invited to Quillon manually before SCIM was enabled, or when the same person exists in two directories. To resolve it, identify the existing Quillon account and decide which record should be authoritative. If the existing account was created manually, you can convert it to a provisioned account by re-running the sync after removing the manual invitation, or by asking Quillon support to link the two records. Do not delete the existing account while contracts, approvals, or signatures are attached to it, because those records must remain attributable to the original user. If the email address belongs to a different person, correct the email in the directory and retry.

If provisioning succeeds but the user cannot sign in, confirm that the account is active, that the email address matches the sign-in identity, and that the user has accepted any workspace invitation that was sent. If single sign-on is enabled, check that the user's identity provider session is pointing at the correct tenant.

If a deactivated user still appears active, check whether your identity provider has finished the scheduled sync. Then confirm that the deactivation was applied to the directory account rather than only to the application assignment. Removing the application assignment is a separate action in some providers and may not trigger a deactivation call.

For problems not covered here, collect the identity provider's provisioning log entries, the Quillon user record reference, and the time of the event, then contact Quillon support through the Help menu in the workspace.
