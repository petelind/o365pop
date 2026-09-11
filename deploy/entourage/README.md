# Mac `taskd` — Entourage Tasks + Calendar sync

LibreELEC publishes `/storage/o365pop/tasks/snapshot.json` and `/storage/o365pop/calendar/snapshot.json`. This host applies both to Entourage 2008 every 60 seconds via Apple Events. The Mac never calls Microsoft Graph and never holds Azure tokens.

## What the operator mounts

`TASK_SNAPSHOT_PATH` must be a regular file this Mac can read (SMB/NFS mount, rsync drop, or a shared folder). Missing or unreadable path is TASK1.8: WARNING `reachability=down`, Entourage unchanged, exit 0.

Receipts are written next to the snapshot:

```
tasks/snapshot.json
tasks/receipts/new/{uid}.json
```

LibreELEC `sync_tasks` applies `receipts/new` and moves files to `sent/` or `failed/`.

Calendar uses the same hop shape:

```
calendar/snapshot.json
calendar/attachments/{eventId}/{filename}
calendar/receipts/new/{uid-or-localKey}.json
calendar/acks/{localKey}.json   # LibreELEC writes after POST create
```

LibreELEC `sync_calendar` applies calendar receipts and writes create acks. Missing or unreadable `CAL_SNAPSHOT_PATH` is CAL1.8 (same as TASK1.8): WARNING `reachability=down`, exit 0; TASK apply still runs when configured.

## Azure (human, once)

On the Azure app add `Tasks.ReadWrite`, `Calendars.ReadWrite`, and `MailboxSettings.Read`. Then on LibreELEC:

```bash
make login
```

`GRAPH_SCOPES` in `o365pop/accounts/graph_auth.py` must include those two names so login actually requests them.

## Install on the Entourage Mac (10.14)

Python 3.12+ is enough (stdlib only). Office 2008 / Entourage must be installed.

1. Copy this repo (or at least `deploy/entourage/`) onto the Mac.
2. Point `TASK_SNAPSHOT_PATH` and `CAL_SNAPSHOT_PATH` at the mounted snapshots.
3. Copy `com.o365pop.taskd.plist` to `~/Library/LaunchAgents/`.
4. Replace `/REPLACE/WITH/o365pop/checkout` and `/Users/REPLACE` in the plist.
5. Confirm `/usr/local/bin/python3` exists (or edit `ProgramArguments`).
6. Load:

```bash
launchctl load ~/Library/LaunchAgents/com.o365pop.taskd.plist
```

Manual tick:

```bash
cd /path/to/o365pop
TASK_SNAPSHOT_PATH=/Volumes/o365pop/tasks/snapshot.json \
CAL_SNAPSHOT_PATH=/Volumes/o365pop/calendar/snapshot.json \
  /usr/local/bin/python3 -m deploy.entourage
```

## Color names

Starter map is in `color_map.py`. If live Entourage rejects a `category color` token, fix that table — it is a data change, not a new SAO decision.

## Do not

- Do not import `o365pop.graph` on this Mac
- Do not write Entourage’s `Database` file
- Do not add an HTTP server for the snapshot
- Do not run `osascript` in `make test` (CI uses `FakeEntourage`)
