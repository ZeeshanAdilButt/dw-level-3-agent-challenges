---
title: Connector sync errors
audience: public
owner_scope: everyone
authority: guide
version_chain: sup-sync-errors
effective_from: '2026-07-15'
supersedes: null
links:
- doc-integ-salesforce
type: support
doc_id: doc-sup-sync-errors
---

# Connector sync errors

## Overview

This guide explains what to do when a connected system fails to sync with Quillon. Connector sync errors appear in the Connectors panel and in the activity log for the affected workspace. Most sync errors clear without action, but some need a quick check on your side.

## What ERR-SYNC-502 means

ERR-SYNC-502 means the connected system timed out before it returned a response to Quillon. Quillon retries the sync every 10 minutes until the connection responds again. No contract data is lost during a retry, and records already synced stay in place.

## Steps to resolve a sync error

1. Open the Connectors panel and select the connection that shows the error.
2. Note the error code and the time of the last successful sync.
3. Confirm that the connected system is online and available to other users.
4. Check that your login for the connected system has not expired or been changed.
5. Wait for the next automatic retry, which occurs every 10 minutes.
6. If the error remains after three retries, select Reconnect and sign in again.
7. If the error still appears after reconnecting, contact Quillon Support and include the error code, the connection name, and the approximate time of the failure.

## Tip

Schedule large imports or bulk updates outside peak working hours for the connected system. Timeouts are more common when the other system is busy, and a quieter window reduces the chance of ERR-SYNC-502 appearing during your work.
