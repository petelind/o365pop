# ==============================================================================
# o365pop — single orchestration layer (BSP-06, SAO §15)
# No Django / npm. CI calls these targets.
# ==============================================================================

.PHONY: help provision run status test test-unit test-integration lint format \
	typecheck precommit db-init worker beat popd smtpd login clean clean-all \
	_check-prereqs _venv _pip-install _db-init

.DEFAULT_GOAL := help

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
PYTHON3 := python3

# ==============================================================================
##@ General
# ==============================================================================

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\t\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

# ==============================================================================
##@ Provision
# ==============================================================================

provision: _check-prereqs _venv _pip-install _db-init ## Install prerequisites, deps, SQLite schema
	@echo "✅ Provisioning complete. Run 'make status' or 'make test'."

_check-prereqs:
	@echo "Checking prerequisites..."
	@command -v $(PYTHON3) >/dev/null 2>&1 || { echo "❌ python3 not found"; exit 1; }
	@$(PYTHON3) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 14) else 1)' \
		|| { echo "❌ Python 3.14+ required (found $$($(PYTHON3) --version))"; exit 1; }
	@command -v git >/dev/null 2>&1 || { echo "❌ git not found"; exit 1; }
	@echo "✅ Prerequisites OK ($$($(PYTHON3) --version))"

_venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment with $(PYTHON3)..."; \
		$(PYTHON3) -m venv $(VENV); \
		$(PIP) install --upgrade pip; \
	else \
		echo "✅ Virtual environment exists"; \
	fi

_pip-install:
	@echo "Installing Python dependencies..."
	@$(PIP) install -r requirements.txt -q

_db-init:
	@echo "Initializing SQLite schema..."
	@$(PYTHON) -m o365pop init-db

# ==============================================================================
##@ Development
# ==============================================================================

run: status ## Alias for status (no HTTP server)

status: ## Print CLI health check
	@$(PYTHON) -m o365pop status

worker: ## Start Celery worker
	@$(PYTHON) -m celery -A o365pop.celery_app:celery_app worker -l info

beat: ## Start Celery beat
	@$(PYTHON) -m celery -A o365pop.celery_app:celery_app beat -l info

popd: ## Start POP3 daemon (AUTH/POP feature)
	@$(PYTHON) -m o365pop popd

smtpd: ## Start SMTP daemon (SMTP feature)
	@$(PYTHON) -m o365pop smtpd

login: ## Device-code Microsoft login (AUTH feature)
	@$(PYTHON) -m o365pop login

db-init: _db-init ## Recreate / apply SQLite schema

# ==============================================================================
##@ Testing
# ==============================================================================

test: ## Run all tests
	@$(PYTEST) tests/ -v --tb=short

test-unit: ## Run unit tests only
	@$(PYTEST) tests/unit/ -v --tb=short

test-integration: ## Run integration tests only
	@$(PYTEST) tests/integration/ -v --tb=short

# ==============================================================================
##@ Code Quality
# ==============================================================================

lint: ## Run linter (ruff check)
	@$(VENV)/bin/ruff check .

format: ## Auto-format code (ruff format)
	@$(VENV)/bin/ruff format .
	@$(VENV)/bin/ruff check --fix .

typecheck: ## Type checker placeholder (mypy not in v1)
	@echo "mypy not configured — skipping"

precommit: ## Run all pre-commit hooks
	@$(VENV)/bin/pre-commit run --all-files

# ==============================================================================
##@ Cleanup
# ==============================================================================

clean: ## Remove build artifacts, caches, logs
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .pytest_cache htmlcov .coverage coverage.xml .ruff_cache
	@rm -f tests.log
	@echo "✅ Cleaned"

clean-all: clean ## Remove everything including venv
	@rm -rf $(VENV)
	@echo "✅ Cleaned all (including venv)"
