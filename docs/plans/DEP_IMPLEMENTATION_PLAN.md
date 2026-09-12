# DEP — Implementation Plan

**Feature**: DEP LibreELEC Docker stack behind WireGuard
**Feature File**: `docs/features/act-1-bridge/deploy.feature`
**Scenarios**: DEP1.1
**GitHub Issues**: none yet
**Branch**: `feature/deploy-libreelec`
**Agent**: Dr. Dobbs v2
**Prerequisites**: POP + SMTP + TEAM checkpoints green (images must have all entrypoints)

BPE-01 adjustments: no cloud/Helm. Compose + bind-config tests. Manual Entourage smoke is operator DoD, not CI.

---

## Context Map

| File | Lines | Note |
|------|-------|------|
| `docs/features/act-1-bridge/deploy.feature` | 1–13 | DEP1.1 |
| `docs/architecture/SAO.md` | §8, §12, §13 | host network, `/storage/o365pop`, WG bind, no WAN |
| `o365pop/config.py` | (BOOT) | Add `POP3_BIND`, `SMTP_BIND`, `ALLOW_LAN` here |
| `o365pop/popd/service.py` | (POP) | Listen using config bind — do not hardcode 0.0.0.0 |
| `o365pop/smtpd/` | (SMTP) | Same bind rules |

---

## Do Not Do

- Do NOT default listen to `0.0.0.0` when `ALLOW_LAN` is unset
- Do NOT bind 110/587 on the WAN NIC
- Do NOT put secrets in the image (`.env` is a volume)
- Do NOT add TLS to popd/smtpd
- Do NOT add Kubernetes/Helm
- Do NOT require live Graph in CI

---

## SAO.md Sections That Apply

- §8 Infrastructure
- §10 Release & Rollback (image + volumes)
- §12 Config & Secrets
- §13 Security
- §14 Backup & Recovery

---

## Current State Assessment

**Exists:** five processes as local make targets.
**Missing:** Dockerfile, compose, bind guards, LibreELEC volume notes.

---

## Clarifications

None. Host network. Redis sidecar.

---

## Implementation Plan

Rules: `do-test-first`, `do-small-increments`, `do-informative-logging`

### DEP1.1 Compose + bind policy

- [x] **1.1** `config.validate_bind()` — require `POP3_BIND`/`SMTP_BIND`; reject unspecified WAN; `ALLOW_LAN=1` is the only way to listen on all interfaces
- [x] **1.2** Red: `tests/unit/test_bind_config.py`
- [x] **1.3** `deploy/Dockerfile` — Python 3.12+; entrypoints `worker`, `beat`, `popd`, `smtpd`
- [x] **1.4** `deploy/docker-compose.yml` — redis, worker, beat, popd, smtpd; `network_mode: host`; volumes `data`, `maildir`, `spool`, `logs`
- [x] **1.5** `deploy/libreelec/README.md` — `/storage/o365pop`, device-code over SSH, Entourage 110/587 no SSL
- [x] **1.6** Wire popd/smtpd to `validate_bind` at startup (log `config` beat with bind+port, never password)
- **Commit**: `feat(deploy): LibreELEC compose and WireGuard bind defaults`

**Checkpoint**: `pytest tests/unit/test_bind_config.py -x`

**Operator smoke (not CI):** login, sync, Entourage POP+SMTP over WG, Reply on a Teams-as-email.

---

## Tests (explicit)

| Test | Proves |
|---|---|
| `test_bind_config` | DEP1.1 bind policy |

Compose “listens on 110/587” is documented + operator smoke. A CI docker-compose up is optional later, not this slice.

---

## Definition of Done

- [x] Checkpoint green
- [x] README lists volumes and Entourage settings
- [x] `pytest tests/ -x` for the whole repo
- [x] Feature files annotated implemented after operator smoke

---

## Lessons Learned

*(fill during execute)*
