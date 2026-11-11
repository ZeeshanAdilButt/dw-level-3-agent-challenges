---
title: Workflow automation connector
audience: public
owner_scope: everyone
authority: guide
version_chain: integ-workflow
effective_from: '2026-07-01'
supersedes: null
links: []
type: integration
doc_id: doc-integ-workflow
---

# Workflow automation connector

## Purpose

The workflow automation connector links Quillon contract management with the automation tools your team already uses. When something happens to a contract in Quillon, the connector can send that event to another system, and it can accept instructions back so that routine steps run without manual handling. This guide explains what the connector does, who can use it, how to set it up, and the limits to plan around.

## What the connector does

The connector can trigger on 6 events, including contract signed. The other events cover moments such as a draft being created from a template, an approval being requested or completed, an obligation coming due, and a renewal alert being raised. Each event carries the contract identifier, the event type, the time it occurred, and the name of the user or system that caused it.

When a trigger fires, your automation tool receives the event and can then perform an action, such as creating a task in a project tracker, posting a message to a team channel, or updating a record in another system. Actions flow back into Quillon only where the connector exposes them, and the list of available actions is shown in the connector settings.

## Who can use it

Only users with administrator rights in the Quillon workspace can install and configure the connector. Other users can see the events that a connector sends, but they cannot change which events are sent or where they go. Workspace owners should review the connector list periodically and remove any connection that is no longer needed.

## Setup steps

1. Sign in to Quillon with an administrator account and open the integrations area from the workspace settings menu.
2. Select the workflow automation connector and choose the option to create a new connection.
3. Enter a name for the connection that makes its purpose clear to other administrators, such as the team or process it supports.
4. Copy the connection credential that Quillon generates and paste it into your automation tool. Store the credential in your tool's secure settings and do not share it in email or chat.
5. In the event list, select the events that should trigger the connection. Start with a small number so you can confirm behavior before adding more.
6. Choose the contract types or folders the connection should cover. Leave this set to all contracts only if every downstream step is appropriate for every contract.
7. Send a test event from the connector settings and confirm that your automation tool received it and ran the expected step.
8. Save the connection and record its owner, so that someone is responsible for updates when the downstream process changes.

## Limits and planning notes

Events are delivered in the order they occur for a single contract, but delivery between separate contracts is not guaranteed to follow any particular sequence. Downstream steps should therefore not depend on the order of events across different contracts.

If the receiving system is unavailable, Quillon retries delivery for a limited period. Events that still cannot be delivered after the retry window are listed in the connector's activity log, where an administrator can resend them manually.

The connector passes on the contract data described in the event payload. Teams should review which fields leave Quillon before connecting a third-party tool, particularly where contracts contain confidential or regulated information. Actions cannot change signed contracts. Signed documents remain read-only in Quillon, and any automation that targets them is limited to recording, notifying, or tracking.

For questions about a specific setup, contact the Quillon support team through the help center and include the connection name and a copy of the relevant activity log entry.
