# o365pop on LibreELEC

Volumes (persist on `/storage`):

- `/storage/o365pop/.env` — secrets (`TOKEN_ENCRYPTION_KEY`, Azure ids, local mailbox password)
- `/storage/o365pop/data` — sqlite, maildir, spool
- `/storage/o365pop/logs` — `app.log`

`POP3_BIND` / `SMTP_BIND` = WireGuard address. Leave `ALLOW_LAN` unset.

Entourage 2008: POP 110 no SSL, SMTP 587 no SSL, SMTP auth on, same local user/password. Not the Microsoft password.

Login: `docker exec` / SSH → `python -m o365pop login` (device code on another device).
