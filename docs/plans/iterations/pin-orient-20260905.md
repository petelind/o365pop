## Orient Summary — 2026-09-05 (Edda v73 PIN re-run)

### Target
Act: act-1-bridge
Feature files:
- `docs/features/act-1-bridge/auth.feature`
- `docs/features/act-1-bridge/inbound.feature`
- `docs/features/act-1-bridge/pop.feature`
- `docs/features/act-1-bridge/smtp.feature`
- `docs/features/act-1-bridge/teams.feature`
- `docs/features/act-1-bridge/deploy.feature`

BOOT has no `.feature` file (scaffold). Journey acts 1–4 map to AUTH → SYNC/POP → SMTP/SEND → TEAM.

### Scenarios in Scope
| ID | Title | MIN status (re-run) |
|---|---|---|
| S1 | BOOT Scaffold package, Celery, SQLite, logging | done (#1 closed) |
| S2 | AUTH Device-code login and token vault | done (#2 closed) |
| S3 | SYNC Graph pull, tosser, and maildir | done (#3 closed) |
| S4 | POP Twisted mailbox for Entourage | done (#4 closed) |
| S5 | SMTP aiosmtpd spool and sendMail scanner | in-progress (#5; SMTP1.1 green, SEND1.1–1.2 open) |
| S6 | TEAM Reply map — chat post not sendMail | queued (#6) |
| S7 | DEP LibreELEC bind policy and compose | queued (#7) |

`scope_override: confirmed` — human already directed the full act in one iteration. Re-run does not shrink or add scenarios.

### Scenarios Deferred
None

### Velocity Trend
First iteration — no `docs/lessons_learned/ITER-*.md`. `docs/lessons_learned/log.yaml` ignored (deprecated).

### Dominant Drift
None — first iteration. In-flight note: shared files stay serialized (`sync/tasks.py`, `graph/`, `tosser/outbound_scanner.py`, bind config).

### Scope Validation
No historical velocity/footprint risk. Complexity is high (new Graph, daemons, Teams map) but already contracted and half-shipped. Do not split mid-flight.

### PIN-01
- `target_act`: act-1-bridge
- `has_mockups`: false (SAO §1 — no GUI; proceed with feature specs)
- `agent_harness`: n/a
