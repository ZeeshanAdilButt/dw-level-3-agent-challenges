---
title: Slack app
audience: public
owner_scope: everyone
authority: guide
version_chain: integ-slack
effective_from: '2026-07-01'
supersedes: null
links: []
type: integration
doc_id: doc-integ-slack
---

# Slack app

## Overview

The Quillon Slack app brings contract approvals, obligation alerts and contract search into the Slack workspace your team already uses. It is designed for legal teams, procurement staff and corporate finance teams who want to act on contract work without switching to the Quillon web application. The app does not replace the main product: drafting, the clause library and e-signature remain in Quillon, while Slack handles notifications, quick responses and lookups.

## Who can use the app

The Slack app is available on the Team, Pro and Enterprise plans. Workspace administrators install the app, and each person who uses it must link their Slack account to a Quillon user account. Users see only the contracts and approvals they already have permission to view in Quillon, so the app never exposes more information than the web application would.

## Before you start

Before installing, confirm the following:

1. Your Quillon organization is on the Team, Pro and Enterprise plans, or a higher tier that includes them.
2. You hold administrator rights in both your Slack workspace and your Quillon organization.
3. Your Slack workspace allows apps to be installed by administrators.
4. Each user who will use the app has an active Quillon account using the same work email address as their Slack profile.

## Setup steps

Follow these steps to install and configure the app.

1. In Quillon, open Settings, then Integrations, and select Slack.
2. Select Add to Slack and sign in to the Slack workspace you want to connect.
3. Review the requested permissions and approve the installation. The permissions cover posting messages, reading user profile details and responding to slash commands.
4. Choose the default channel for renewal alerts and obligation reminders. You can change this later for individual contract types.
5. Ask each user to open Quillon, go to Profile, then Connected accounts, and select Link Slack. This step confirms the identity behind each Slack user.
6. Send a test message by running a command in any channel where the app has been added, and confirm that the response appears.

## Using the app

Once users have linked their accounts, the following commands are available in Slack:

- The Slack command /quillon approvals lists your pending approvals. Each item shows the contract name, the requesting party and the date the request was made. You can select an item to open it in Quillon.
- Renewal alerts and obligation reminders post automatically to the channel you chose during setup, and tag the contract owner.
- Search across signed contracts is available by typing a short query in the app's message box. Results show only documents you are permitted to view.

Approvals can be approved or returned directly from a Slack message where your organization has enabled this option. Where it is not enabled, the message links to the approval screen in Quillon.

## Limits

The following limits apply to the Slack app:

- The app reads and posts only in channels where it has been invited. It does not read private messages between users.
- Approval actions taken in Slack are recorded in the same audit history as actions taken in Quillon.
- Search results in Slack return a summary and a link. Full document text is viewed in Quillon.
- If a user's Quillon account is deactivated, their Slack commands stop returning results immediately.
- Notification delivery depends on Slack's service availability. Pending items remain visible in Quillon when Slack is unavailable.
- Changes to a user's Quillon permissions take effect in Slack the next time they run a command.

## Getting help

If you have trouble installing the app or linking accounts, contact your Quillon administrator first. Organizations can contact Quillon support through the Help menu in the web application.
