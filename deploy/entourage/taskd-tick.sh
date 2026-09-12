#!/bin/sh
# Pull snapshots from LibreELEC, apply to Entourage, push receipts back.
set -eu
export HOME="${HOME:-/Users/denispetelin}"
LOCK="/tmp/o365pop-taskd.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  exit 0
fi
trap 'rmdir "$LOCK"' EXIT INT TERM

export PYTHONPATH="$HOME/o365pop"
export TASK_STATE_DIR="$HOME/Library/Application Support/o365pop"
export TASK_LOG_PATH="$HOME/Library/Logs/o365pop-taskd.log"

TASK_DEST="$TASK_STATE_DIR/tasks"
CAL_DEST="$TASK_STATE_DIR/calendar"
mkdir -p \
  "$TASK_DEST/receipts/new" "$TASK_DEST/receipts/sent" \
  "$CAL_DEST/receipts/new" "$CAL_DEST/receipts/sent" \
  "$CAL_DEST/acks" "$CAL_DEST/attachments"

export TASK_SNAPSHOT_PATH="$TASK_DEST/snapshot.json"
export CAL_SNAPSHOT_PATH="$CAL_DEST/snapshot.json"

SCP="scp -o BatchMode=yes -o ConnectTimeout=60"
LE="root@192.168.0.130"

_push_receipts() {
  local src="$1"
  local remote="$2"
  if ls "$src"/*.json >/dev/null 2>&1; then
    $SCP "$src"/*.json "$remote" && rm -f "$src"/*.json
  fi
}

_push_receipts "$TASK_DEST/receipts/new" "$LE:/storage/o365pop/var/tasks/receipts/new/"
_push_receipts "$CAL_DEST/receipts/new" "$LE:/storage/o365pop/var/calendar/receipts/new/"

$SCP "$LE:/storage/o365pop/var/tasks/snapshot.json" "$TASK_DEST/snapshot.json" || true
$SCP "$LE:/storage/o365pop/var/calendar/snapshot.json" "$CAL_DEST/snapshot.json" || true

$SCP -r "$LE:/storage/o365pop/var/calendar/attachments/." "$CAL_DEST/attachments/" 2>/dev/null || true
$SCP "$LE:/storage/o365pop/var/calendar/acks/"*.json "$CAL_DEST/acks/" 2>/dev/null || true

TASK_SNAPSHOT_PATH="$TASK_SNAPSHOT_PATH" CAL_SNAPSHOT_PATH= /usr/local/bin/python3 -m deploy.entourage || true
TASK_SNAPSHOT_PATH= CAL_SNAPSHOT_PATH="$CAL_SNAPSHOT_PATH" /usr/local/bin/python3 -m deploy.entourage || true

_push_receipts "$TASK_DEST/receipts/new" "$LE:/storage/o365pop/var/tasks/receipts/new/"
_push_receipts "$CAL_DEST/receipts/new" "$LE:/storage/o365pop/var/calendar/receipts/new/"

exit 0
