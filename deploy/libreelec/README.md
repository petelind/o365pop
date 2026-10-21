# A Raspberry Pi “Palm HotSync server” on LibreELEC

> **Illustrative only; use is explicitly discouraged. No warranty.** Use disposable accounts and an isolated lab network. POP/SMTP, Network HotSync, and Palm-facing HTTP are cleartext. Never port-forward them. See the [root disclaimer](../../README.md) and [LICENSE](../../LICENSE).

The lean launcher runs Redis plus one Python container containing worker, beat, POP, SMTP, and optional ModernHotSync. It uses host networking and persistent checkouts under `/storage`. The web proxy runs separately. USB is not passed through.

## 1. Copy the projects

Install/enable Docker on your LibreELEC device first. From a modern machine, clone the three projects as described in [ModernHotSync](https://github.com/petelind/ModernHotSync). Copy their **source** to:

```text
/storage/o365pop/        # container /app
/storage/modernhotsync/  # container /mhs
/storage/palmproxy/      # separate proxy container /proxy
```

Use SSH/scp, rsync, or an archive transfer. Do not copy your Mac/PC `.venv`: Linux/ARM needs its own environment. Exclude `.git`, `.venv`, `.env`, runtime `var`/`logs`, and local reference material. Create the destination directories first. On systems with Git, cloning directly to these directories is also possible.

Replace `192.168.50.2` throughout this guide with the Pi's isolated lab address. Ensure the Palm can reach it. Permit only the intended lab clients and keep Redis restricted to the host. The launcher uses Redis's default host-network listener; protect port 6379 with host/network rules before starting it.

## 2. Create the Python environment on the Pi

From the Pi's SSH shell:

```sh
docker run --rm \
  -v /storage/o365pop:/app \
  -v /storage/modernhotsync:/mhs \
  -w /app python:3.12-slim sh -c '
    python -m venv /app/.venv &&
    /app/.venv/bin/python -m pip install -r /app/requirements.txt &&
    /app/.venv/bin/python -m pip install -e /mhs
  '
```

This installs both projects' dependencies in the environment the launcher uses. On older 32-bit ARM devices, some dependencies may need build tools or a different supported base image; the image/install must succeed before continuing. Do not assume every Pi generation is supported.

## 3. Configure o365pop

Register your own Entra app with the permissions in the [root setup guide](../../README.md#setup). Copy `.env.example` to `/storage/o365pop/.env` and edit it. Paths below are **inside the container**:

```dotenv
AZURE_CLIENT_ID=your-own-application-client-id
AZURE_TENANT_ID=your-tenant-id-or-common
TOKEN_ENCRYPTION_KEY=your-generated-fernet-key
MAILBOX_USER=retro
MAILBOX_PASSWORD=a-separate-local-test-password
POP3_BIND=192.168.50.2
POP3_PORT=110
SMTP_BIND=192.168.50.2
SMTP_PORT=587
ALLOW_LAN=1
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
DATA_DIR=/app/var
DB_PATH=/app/var/o365pop.sqlite3
LOG_DIR=/app/logs
```

Generate the encryption key on the Pi, then copy it into that file:

```sh
docker run --rm -v /storage/o365pop:/app python:3.12-slim \
  /app/.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
chmod 600 /storage/o365pop/.env
```

Do not replace an existing key if you want to retain its encrypted token vault.

## 4. Configure ModernHotSync

Create `/storage/modernhotsync/.env`:

```dotenv
O365POP_ROOT=/app
O365POP_ENV=/app/.env
DATA_DIR=/app/var
MHS_DB_PATH=/app/var/modernhotsync.sqlite3
LOG_DIR=/app/logs
TRANSPORT=network
NETSYNC_HOST=192.168.50.2
NETSYNC_PORT=14238
DEVICE_TZ=America/New_York
DEFAULT_TODO_LIST_NAME=Tasks
```

The mapping database and o365pop token database **must have different paths**. Microsoft settings/key are inherited from o365pop. Do not set `DB_PATH` to `modernhotsync.sqlite3`.

## 5. Log in, then start

Run device-code login in a temporary container before starting the background services:

```sh
docker run --rm -it --network host \
  --env-file /storage/o365pop/.env \
  -v /storage/o365pop:/app -w /app python:3.12-slim \
  /app/.venv/bin/python -m o365pop login
```

Complete consent in a browser on another device. If your tenant blocks device-code login, complete the interactive login on a modern machine and transfer the matching test-account vault and configuration securely; the browser callback must reach the machine performing login. Never publish either file.

```sh
chmod +x /storage/o365pop/deploy/libreelec/start.sh \
  /storage/o365pop/deploy/libreelec/run-daemons.sh
/storage/o365pop/deploy/libreelec/start.sh
docker logs --tail 50 o365pop
```

The launcher expects `/app/.venv/bin/python` already to exist. Installing dependencies is the separate step above. If containers already exist, `start.sh` starts them with their original mounts/environment; it does not recreate them. After changing container environment or adding the ModernHotSync mount, stop/remove the **container only** and rerun the launcher; retain `/storage` data and backups.

On the Palm:

- VersaMail POP: Pi address, port **110**, user **palm**, local mailbox password, SSL off.
- SMTP: Pi address, port **587**, AUTH LOGIN with `MAILBOX_USER` and the local password, SSL off.
- HotSync: **Network**, Primary PC Address = Pi address. Permit **UDP 14237 + TCP 14238**. Do not run another HotSync listener at the same time.

Full HotSync can change both Microsoft and Palm records. For handshake/read-only trials, first use [ModernHotSync's local procedures](https://github.com/petelind/ModernHotSync#4-connect-the-palm) with backups and disposable data; the automatic launcher starts full sync.

## 6. Add the web proxy

Prepare a separate ARM/Linux environment:

```sh
docker run --rm -v /storage/palmproxy:/proxy -w /proxy \
  python:3.12-slim sh -c '
    python -m venv /proxy/.venv &&
    /proxy/.venv/bin/python -m pip install -r requirements.txt &&
    /proxy/.venv/bin/python -m pip install -e .
  '
docker run -d --name palmproxy --network host --restart unless-stopped \
  -v /storage/palmproxy:/proxy -w /proxy \
  -e PALMPROXY_HOST=192.168.50.2 \
  -e PALMPROXY_ALLOW_CIDR=192.168.50.0/24,127.0.0.0/8 \
  python:3.12-slim /proxy/.venv/bin/python -m palmproxy
```

In Blazer's advanced proxy settings enter the Pi IP and port **8080**. Open `http://192.168.50.2:8080/`. See [palmproxy](https://github.com/petelind/palmproxy) for browser limitations. It serves simplified pages over HTTP, without end-to-end TLS to the handheld.

## 7. Autostart and operate

Add this line to an existing `/storage/.config/autostart.sh`, preserving any existing commands:

```sh
/storage/o365pop/deploy/libreelec/start.sh
```

If creating that file, include `#!/bin/sh` and mark it executable. Docker must be ready before the launcher runs; if boot logs show a Docker startup race, arrange the startup order on your host. Existing containers use `restart: unless-stopped`; the proxy has the same restart policy.

Useful checks:

```sh
docker ps
docker exec o365pop /app/.venv/bin/python -m o365pop status
docker logs --tail 50 o365pop
docker logs --tail 50 palmproxy
```

The status command checks bootstrap health, not a complete sync. Verify a test email, disposable calendar/task/memo, and a public article from the Palm separately. Runtime state lives in `/storage/o365pop/var`, including maildir/spool, tokens, snapshots, receipts, and Palm mappings. Logs are under `/storage/o365pop/logs`; protect and redact them.

The old `deploy/docker-compose.yml` is a separate, historical layout with a relative build context and different mounts. It is not interchangeable with this launcher.
