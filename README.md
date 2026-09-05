# o365pop

Local LibreELEC daemon that lets vintage POP/SMTP clients (Entourage 2008) talk to Microsoft 365.

## Quick Start

```bash
make provision   # Create .venv, install deps, init SQLite schema
make test        # Run pytest
python -m o365pop status   # Health check (no web UI)
```

There is no HTTP welcome page. Operator surface is the CLI plus `logs/app.log`.

## Development

| Command          | Description                         |
|------------------|-------------------------------------|
| `make provision` | Install prerequisites and dependencies |
| `make test`      | Merge-gate tests (excludes live Graph) |
| `make test-unit` | Unit tests only                     |
| `make test-integration` | Integration tests (no mocks) |
| `make test-log-story` | Caplog beat proofs              |
| `make test-e2e`  | Live journey (device-code once, then POP/SMTP) |
| `make test-watch` | Re-run tests on `.py` changes      |
| `make lint`      | Run ruff                            |
| `make format`    | Auto-format with ruff               |
| `make status`    | CLI health check                    |
| `make worker`    | Start Celery worker                 |
| `make beat`      | Start Celery beat                   |
| `make popd`      | Start POP3 daemon                   |
| `make smtpd`     | Start SMTP daemon                   |
| `make login`     | Device-code Microsoft login         |
| `make clean`     | Remove build artifacts              |
| `make help`      | Show all targets                    |

`make test-e2e` is operator-only (not the merge gate). First run prints a Microsoft device-code; tokens stay in `var/live-e2e/`.

## Documentation

- [System Architecture Overview](docs/architecture/SAO.md)
- [Modus operandi](docs/process/MODUS_OPERANDI.md) — Cursor ADE + delivery loop
- [Phrase catalog](docs/features/CATALOG.md) · [Fixture catalog](tests/fixtures/CATALOG.md)
- [Implementation index](docs/plans/O365POP_IMPLEMENTATION_PLAN.md)
- [User journey](docs/features/user_journey.md)
