# IA Guidelines — o365pop

**ESM-03 (stack-adjusted).** There is **no web UI** (SAO §1). Bootstrap/HTMX/Font Awesome/Playwright rules do not apply to application surfaces.

## Surfaces

| Surface | Audience | Medium |
|---|---|---|
| Operator CLI | Denis | `python -m o365pop` / Makefile (`status`, `login`, `popd`, `smtpd`) |
| Operator log | Denis | `logs/app.log` — `{logger} \| {Class.method} \| {beat} \| key=value` |
| Mail client | Entourage 2008 | POP3 :110, SMTP :587, no TLS, USER/PASS / AUTH LOGIN |
| Compose | Denis | LibreELEC Docker — not an in-app screen |

## Information architecture

- **One mailbox.** No tenant switcher, no account picker.
- **Teams appears as mail.** From/Reply-To are `teams.{chat_b32}@o365pop.local`, never the person’s real SMTP address.
- **Failures are files + logs.** `spool/failed/` and beat `error` — no toast, no modal.

## Operator CLI conventions

- Verbs: `status`, `init-db`, `login`, `popd`, `smtpd`.
- `status` is the health dashboard (BSP-07 substitute). Exit 0 = healthy.
- Never print tokens, mailbox passwords, or raw MIME.
- Disabled/unimplemented commands exit 2 with the owning feature name (AUTH/POP/SMTP).

## Entourage (client “screens”)

Treat Entourage folders and compose windows as the only human mail UI. o365pop must not require SSL, OAuth, or modern IMAP. Local password ≠ Microsoft password.

## Accessibility / E2E selectors

N/A for o365pop itself. Do not add `data-testid` to a non-existent HTML app. Protocol tests use `poplib` / `smtplib`.

## When this file is wrong

If a future operator web console is approved, rewrite this document and lift the SAO §1 “UI: None” lock first — do not sneak in HTMX.
