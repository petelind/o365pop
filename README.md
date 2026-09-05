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
| `make test`      | Run all tests                       |
| `make test-unit` | Run unit tests                      |
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

`popd`, `smtpd`, and `login` are stubs until those features land.

## Documentation

- [System Architecture Overview](docs/architecture/SAO.md)
- [Implementation index](docs/plans/O365POP_IMPLEMENTATION_PLAN.md)
- [User journey](docs/features/user_journey.md)
