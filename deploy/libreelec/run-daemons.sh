#!/bin/sh
# One container: worker, beat, popd, smtpd (LibreELEC RAM cannot host five images).
set -eu
cd /app
export PYTHONPATH=/app
export PYTHONUNBUFFERED=1
PY="${PY:-/app/.venv/bin/python}"

echo "o365pop daemons starting"
"$PY" -m o365pop init-db
"$PY" -m celery -A o365pop.celery_app:celery_app worker -l info --concurrency=1 &
"$PY" -m celery -A o365pop.celery_app:celery_app beat -l info &
"$PY" -m o365pop popd &
"$PY" -m o365pop smtpd &
wait
