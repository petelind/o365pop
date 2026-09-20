#!/bin/sh
# One container: worker, beat, popd, smtpd, optional mhs serve (LibreELEC RAM).
set -eu
cd /app
export PYTHONPATH="${PYTHONPATH:-/app:/mhs/src}"
export PYTHONUNBUFFERED=1
PY="${PY:-/app/.venv/bin/python}"

echo "o365pop daemons starting"
"$PY" -m o365pop init-db
"$PY" -m celery -A o365pop.celery_app:celery_app worker -l info --concurrency=1 &
"$PY" -m celery -A o365pop.celery_app:celery_app beat -l info &
"$PY" -m o365pop popd &
"$PY" -m o365pop smtpd &
if [ -d /mhs/src/modernhotsync ]; then
	echo "modernhotsync serve starting (TCP 14238)"
	"$PY" -m pip install -q httpx msal cryptography python-dotenv
	if [ -f /mhs/.env ]; then
		set -a
		# shellcheck disable=SC1091
		. /mhs/.env
		set +a
	fi
	"$PY" -m modernhotsync serve --transport network &
fi
wait
