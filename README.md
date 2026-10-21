# o365pop — Microsoft 365 for vintage mail clients

A Python bridge that lets a Palm TX's VersaMail and vintage desktop clients such as Entourage 2008 use Microsoft 365 through POP3 and SMTP. The modern host handles OAuth and Microsoft Graph; the old client talks to local, deliberately old-fashioned mail protocols.

> **For illustrative and educational purposes only. You are explicitly encouraged NOT to use this software.** Experimental, unsupported, and unsuitable for production or sensitive data. Provided **AS IS, without warranty of any kind**; see [LICENSE](LICENSE). Credentials and mail travel in cleartext on the legacy connection. Do not put your hedge fund's proprietary emails here, expose these services to the internet, or rely on them to preserve your only copy of any data.

For the **whole Palm setup**—mail, calendar, tasks, memos, web browsing, and a Raspberry Pi HotSync server—start with [ModernHotSync](https://github.com/petelind/ModernHotSync).

## Components

| Need | Component |
|---|---|
| Mail | This repository: Graph → maildir → POP; SMTP → spool → Graph |
| Palm calendar, tasks, memos | [ModernHotSync](https://github.com/petelind/ModernHotSync), USB or Network HotSync |
| Palm Blazer web browsing | [palmproxy](https://github.com/petelind/palmproxy), a simplifying HTTP proxy |
| Entourage Tasks / Calendar | Optional Mac `taskd`; [setup](deploy/entourage/README.md) |

POP and SMTP daemons never call Graph directly. Celery worker/beat do background synchronization, with Redis as broker. There is one Microsoft mailbox per deployment. There is no web UI; the operator interface is the CLI and `logs/app.log`.

## Setup

Use Python **3.12+**, Git, Make, Redis 7, and a Microsoft 365 test account. macOS and Linux are the intended hosts. Use an isolated lab network and disposable data. Preserve a backup before enabling writes.

### 1. Register your own Microsoft Entra app

Create a public-client app registration for your account/tenant. Enable public client flows for device-code login. For browser login (`--interactive`), configure a Mobile and desktop applications redirect URI of **`http://localhost:8400`**.

Configure the delegated Microsoft Graph permissions requested by this code:

```text
Mail.Read
Mail.ReadWrite
Mail.Send
Chat.ReadWrite
User.Read
Tasks.ReadWrite
Calendars.ReadWrite
MailboxSettings.Read
```

The current login requests all these scopes, even if you only use mail. Tenant policy may require admin consent or disallow a login flow. No client secret is used. Use your own application/client ID; none is supplied by this project.

### 2. Install and configure

```sh
git clone https://github.com/petelind/o365pop.git
cd o365pop
make provision PYTHON3=python3.12
cp .env.example .env
.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Copy the generated key into `.env`, then edit the following values. Replace the example address and absolute paths. These high ports avoid needing root for a local experiment:

```dotenv
AZURE_CLIENT_ID=your-own-application-client-id
AZURE_TENANT_ID=your-tenant-id-or-common
TOKEN_ENCRYPTION_KEY=your-generated-fernet-key
MAILBOX_USER=retro
MAILBOX_PASSWORD=a-separate-local-test-password
POP3_BIND=192.168.50.2
POP3_PORT=1110
SMTP_BIND=192.168.50.2
SMTP_PORT=1587
ALLOW_LAN=1
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
DATA_DIR=/absolute/path/palm-lab/o365pop/var
DB_PATH=/absolute/path/palm-lab/o365pop/var/o365pop.sqlite3
LOG_DIR=/absolute/path/palm-lab/o365pop/logs
```

`ALLOW_LAN=1` is an explicit choice to allow this lab LAN bind. Use only an address assigned to your host, with firewall rules limiting access to the lab. A WireGuard-only bind is another option. Avoid wildcard interfaces; never forward these services to the internet. Protect Redis too: it needs no access from the Palm.

Use **absolute paths**, especially when sharing authentication with ModernHotSync. Keep the encryption key: changing it makes existing encrypted tokens unreadable. Set restrictive permissions on `.env`, for example `chmod 600 .env`. The local mailbox password must differ from your Microsoft password.

### 3. Log in

```sh
make login
# If your tenant blocks device-code login, use the local browser:
make login LOGIN_FLAGS=--interactive
```

Complete the Microsoft consent flow. Tokens are stored encrypted in the configured SQLite database. Log in again after changing the local mailbox credentials so they are applied to the account store. Do not commit or share `.env`, databases, snapshots, message stores, spool contents, or logs.

### 4. Start Redis and all four mail processes

Use your local Redis installation, or, with Docker available:

```sh
docker run -d --name palm-lab-redis -p 127.0.0.1:6379:6379 redis:7-alpine
```

Run each of these commands in its **own terminal**, from the checkout:

```sh
make worker
make beat
make popd
make smtpd
```

Worker pulls/sends through Graph; beat schedules the work. The daemons provide the client connections. Starting only POP/SMTP will not fetch or deliver mail. Stop foreground services with Ctrl-C.

```sh
make status
```

This checks bootstrap/schema health; it does not prove a successful Graph poll, running listeners, or a complete Palm sync. Check `LOG_DIR/app.log` and do a disposable receive/send round trip.

### 5. Configure the mail client

| Setting | Palm VersaMail | Entourage / full mailbox view |
|---|---|---|
| Account email address | Your Microsoft mailbox address | Your Microsoft mailbox address |
| POP server | Host's lab/WireGuard IP | Same |
| POP port | `POP3_PORT` (`1110` above) | Same |
| POP username | **`palm`** | `MAILBOX_USER` |
| POP password | `MAILBOX_PASSWORD` | Same |
| POP SSL/TLS | Off | Off |
| SMTP server / port | Host IP / `SMTP_PORT` (`1587` above) | Same |
| SMTP authentication | AUTH LOGIN, `MAILBOX_USER` + local password | Same |
| SMTP SSL/TLS | Off | Off |

The Palm view includes only Outlook mail from the last **24 hours**, flattened to **7-bit plain text**, capped at **5 KB**, without the original MIME attachments. Teams chat messages are omitted from this view. POP deletion in this Palm view hides the local copy; do not treat it as Graph mailbox deletion or a complete mail archive. Leave messages on the server during initial testing.

Calendar, tasks, and memos do **not** arrive through POP. Use [ModernHotSync's setup](https://github.com/petelind/ModernHotSync) for those.

## Raspberry Pi / LibreELEC

See the [LibreELEC walkthrough](deploy/libreelec/README.md) for the two-container mail/HotSync launcher, shared authentication, web proxy, and autostart. On a normal Linux Pi, the same Python/Redis processes can run directly. The LibreELEC network mode uses UDP **14237** and TCP **14238** for Palm HotSync; it does not pass through USB.

The historical five-service [Compose file](deploy/docker-compose.yml) is not the recommended quick start: its relative build context and volume layout require adaptation, and it does not install/start ModernHotSync or palmproxy. Use the documented lean launcher instead.

## Limitations and security

This bridge deliberately preserves cleartext POP3 USER/PASS and SMTP AUTH LOGIN for vintage clients. Isolation is a prerequisite, not a claim of modern security. Mail, snapshots, attachments, and some logs are plaintext on disk; token encryption does not encrypt the mailbox. Graph permissions allow remote changes. Sync is experimental and can lose data.

This repository distributes bridge code, not Palm OS, Microsoft Office, ROMs, SDKs, or commercial abandonware. Obtain any required third-party software lawfully; calling something “abandonware” does not grant redistribution rights. No affiliation with Palm or Microsoft is implied.

## Development and checks

```sh
make lint
make test
```

`make test` excludes `live_graph` tests. It does not log in to Microsoft. `make test-e2e` is an operator-only live journey: it can prompt for login and read/write test data in a real account, so use a disposable one.

| Command | Purpose |
|---|---|
| `make provision` | Create venv, install dependencies, initialize schema |
| `make test-unit` / `make test-integration` | Scoped offline tests |
| `make test-log-story` | Log behavior assertions |
| `make test-watch` | Continuous offline testing |
| `make lint` / `make format` | Check / format Python |
| `make status` | Bootstrap health |
| `make help` | All available targets |

Architecture and contributor documentation: [SAO](docs/architecture/SAO.md), [process](docs/process/MODUS_OPERANDI.md), [implementation index](docs/plans/O365POP_IMPLEMENTATION_PLAN.md), [user journey](docs/features/user_journey.md), [phrase catalog](docs/features/CATALOG.md), and [fixture catalog](tests/fixtures/CATALOG.md).
