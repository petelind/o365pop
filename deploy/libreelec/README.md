# o365pop on LibreELEC

Volumes (persist on `/storage/o365pop`):

- `/storage/o365pop/.env` — secrets (`TOKEN_ENCRYPTION_KEY`, Azure ids, local mailbox password). Not in the image.
- `/storage/o365pop/data` — sqlite
- `/storage/o365pop/maildir` — inbound maildir
- `/storage/o365pop/spool` — outbound spool
- `/storage/o365pop/logs` — `app.log`
- `/storage/o365pop/tasks` — To Do snapshot + receipts for Mac `taskd`

`POP3_BIND` / `SMTP_BIND` = WireGuard address. Leave `ALLOW_LAN` unset so 110/587 do not bind the WAN NIC.

Entourage 2008: POP 110 no SSL, SMTP 587 no SSL, SMTP auth on, same local user/password. Local mailbox password ≠ Microsoft password. Tasks: Mac `taskd` (launchd) pulls `/storage/o365pop/tasks/snapshot.json` every minute — not POP.

Login: SSH / `docker exec` → `python -m o365pop login` (device code on another device).

## Lean host (armv7 / 1GB)

LibreELEC 12 on a 1GB Pi cannot run the five-service Compose file. Use two containers instead:

```sh
/storage/o365pop/deploy/libreelec/start.sh
```

- `o365pop-redis` — `redis:7-alpine`, host network, `restart: unless-stopped`
- `o365pop` — `python:3.12-slim` + venv, runs worker/beat/popd/smtpd and, when `/storage/modernhotsync` is mounted at `/mhs`, `mhs serve --transport network` on TCP **14238**
- Autostart: `/storage/.config/autostart.sh` calls `start.sh`

Bind `POP3_BIND` / `SMTP_BIND` to the LAN or WireGuard address (not `0.0.0.0` unless `ALLOW_LAN=1`).

## Palm TX (ModernHotSync)

Calendar / Tasks / Memos are **not** POP. They are [ModernHotSync](https://github.com/petelind/ModernHotSync) over Network HotSync (TCP 14238) in this same container. Mail on the handheld is still `USER palm` on `:110`.

- Checkout ModernHotSync at `/storage/modernhotsync` (container `/mhs`). Recreate the `o365pop` container after adding the volume (`docker rm -f o365pop` then `start.sh`).
- `O365POP_ROOT=/app` — same Entra app and token vault. Device-code login: `docker exec -it o365pop python -m o365pop login`.
- Palm: HotSync → Network, Primary PC Address = this box's LAN IP. Live steps: ModernHotSync `tests/hardware/README.md`.
- Bind 14238 on the LAN. USB cradle is not passed into this container.
