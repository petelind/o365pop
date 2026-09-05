# o365pop on LibreELEC

Volumes (persist on `/storage/o365pop`):

- `/storage/o365pop/.env` — secrets (`TOKEN_ENCRYPTION_KEY`, Azure ids, local mailbox password). Not in the image.
- `/storage/o365pop/data` — sqlite
- `/storage/o365pop/maildir` — inbound maildir
- `/storage/o365pop/spool` — outbound spool
- `/storage/o365pop/logs` — `app.log`

`POP3_BIND` / `SMTP_BIND` = WireGuard address. Leave `ALLOW_LAN` unset so 110/587 do not bind the WAN NIC.

Entourage 2008: POP 110 no SSL, SMTP 587 no SSL, SMTP auth on, same local user/password. Local mailbox password ≠ Microsoft password.

Login: SSH / `docker exec` → `python -m o365pop login` (device code on another device).
