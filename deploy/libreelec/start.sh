#!/bin/sh
# Start redis + o365pop on LibreELEC (host network, restart unless-stopped).
set -eu
ROOT="${O365POP_ROOT:-/storage/o365pop}"
MHS="${MHS_ROOT:-/storage/modernhotsync}"
MHS_VOL=""
if [ -d "$MHS/src/modernhotsync" ]; then
	MHS_VOL="-v $MHS:/mhs"
fi

if ! docker inspect o365pop-redis >/dev/null 2>&1; then
	docker run -d --name o365pop-redis --network host --restart unless-stopped redis:7-alpine
else
	docker start o365pop-redis >/dev/null 2>&1 || true
fi

if ! docker inspect o365pop >/dev/null 2>&1; then
	# host network: POP/SMTP + ModernHotSync TCP 14238
	docker run -d --name o365pop --network host --restart unless-stopped \
		--env-file "$ROOT/.env" \
		-v "$ROOT:/app" \
		$MHS_VOL \
		-w /app \
		-e PYTHONUNBUFFERED=1 \
		-e PYTHONPATH=/app:/mhs/src \
		-e O365POP_ROOT=/app \
		-e O365POP_ENV=/app/.env \
		-e DATA_DIR=/app/data \
		-e DB_PATH=/app/data/modernhotsync.sqlite3 \
		-e LOG_DIR=/app/logs \
		-e TRANSPORT=network \
		python:3.12-slim \
		/app/deploy/libreelec/run-daemons.sh
else
	docker start o365pop >/dev/null 2>&1 || true
fi
echo "o365pop stack up"
