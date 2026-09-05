# pytest Runner Configuration

**Capability**: TEST_FRAMEWORK
**Stack**: pytest

# Skill: pytest Runner Configuration

**Capability Domain**: TEST_FRAMEWORK
**Technology Stack**: pytest

## Overview

Configuration patterns for pytest test runner, including pytest.ini setup, command-line options, markers, and test discovery patterns.

## Reference Implementation

### Pattern 1: pytest.ini Configuration

```ini
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = mimir.settings
python_files = test_*.py
python_classes = Test*
python_functions = test_*
testpaths = tests

addopts =
    -v
    --strict-markers
    --tb=short
    --disable-warnings
    -p no:warnings
    --log-cli-level=INFO
    --log-file=tests.log
    --log-file-level=INFO
    --log-file-format=%(asctime)s [%(levelname)s] %(message)s
    --log-file-date-format=%Y-%m-%d %H:%M:%S
    --cov-report=term-missing
    --cov-report=html

markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (real dependencies)
    e2e: End-to-end tests (full user journeys)
    slow: Slow running tests
    django_db: Tests that require database access
    agent_proof: Lane 1 PRF control-plane proofs (ScriptedLLM + assert_agent_story)
    quality: Lane 4 TASK-* golden task eval (live LLM, not PR merge gate)
    live_llm: Requires live LLM provider — skip in default PR CI
```

### Pattern 2: Running Tests

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_playbook_service.py

# Run specific test class
pytest tests/unit/test_playbook_service.py::TestPlaybookService

# Run specific test method
pytest tests/unit/test_playbook_service.py::TestPlaybookService::test_create_playbook

# Run with coverage
pytest tests/ --cov=methodology --cov-report=html

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run agent control-plane proofs (lane 1 — when AGENTS_ENABLED)
pytest -m agent_proof tests/integration/agent/

# Run TASK-* quality eval (lane 4 — nightly / manual only)
pytest -m "quality and live_llm" tests/

# Run all except slow tests
pytest -m "not slow"

# Run with specific log level
pytest tests/ --log-cli-level=DEBUG

# Stop on first failure
pytest tests/ -x

# Run last failed tests
pytest tests/ --lf

# Run failed tests first, then others
pytest tests/ --ff

# Run tests in parallel (requires pytest-xdist)
pytest tests/ -n auto
```

### Pattern 3: Test Discovery

```python
# tests/conftest.py
import pytest
from django.contrib.auth.models import User

@pytest.fixture(scope='session')
def django_db_setup():
    """Configure test database."""
    pass

@pytest.fixture
def test_user(db):
    """Create test user."""
    return User.objects.create_user(
        username='testuser',
        password='testpass123'
    )

@pytest.fixture
def authenticated_client(client, test_user):
    """Create authenticated test client."""
    client.login(username='testuser', password='testpass123')
    return client
```

### Pattern 4: Makefile Targets

```makefile
# Makefile
.PHONY: test test-unit test-integration test-e2e test-cov test-agent-proof test-agent-quality

test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v -m unit

test-integration:
	pytest tests/integration/ -v -m integration

test-e2e:
	pytest tests/e2e/ -v -m e2e

test-agent-proof:
ifeq ($(AGENTS_ENABLED),true)
	pytest tests/integration/agent/ -v -m agent_proof
else
	@echo "skip: agents N/A (SAO §17)"
endif

test-agent-quality:
ifeq ($(AGENTS_ENABLED),true)
	pytest tests/ -v -m quality
else
	@echo "skip: agents N/A (SAO §17)"
endif

test-cov:
	pytest tests/ --cov=methodology --cov-report=html --cov-report=term

test-watch:
	python continuous_test_runner.py

test-failed:
	pytest tests/ --lf -v
```

## Agent pytest markers (when SAO §17 applies)

| Marker | Lane | Default PR CI | Requires |
|--------|------|---------------|----------|
| `agent_proof` | 1 | When `AGENTS_ENABLED=true` | CAP-004 ScriptedLLM, `tests/support/agent_story.py` |
| `quality` | 4 | No — nightly / promotion | Golden task fixtures under `tests/fixtures/agent_tasks/` |
| `live_llm` | 3–4 | No | Provider credentials or Ollama; temp=0 for eval |

**CI rules:**
- Do **not** add `-m agent_proof` to default `ci.yml` until PRF tests exist (empty collection fails).
- Never combine `live_llm` with PR merge gates — use separate `agent-eval.yml`.
- Lane 2 deterministic shell tests use `integration` marker only — no `agent_proof`.

Register all markers in `pytest.ini` with `--strict-markers` to catch typos.

## Common Pitfalls

### ❌ Don't: Run tests without configuration
```bash
# Wrong - no pytest.ini
pytest
```

### ✅ Do: Use pytest.ini for consistent configuration
```ini
# Correct - pytest.ini with settings
[pytest]
testpaths = tests
addopts = -v --tb=short
```

### ❌ Don't: Mix test discovery patterns
```python
# Wrong - inconsistent naming
def check_playbook():  # Won't be discovered
class PlaybookTests:   # Won't be discovered
```

### ✅ Do: Follow pytest conventions
```python
# Correct - pytest discovers these
def test_playbook():
class TestPlaybook:
```

### ❌ Don't: Run `@live_llm` tests in default PR CI
```bash
# Wrong — flaky and credential-dependent
pytest -m live_llm
```

### ✅ Do: Gate live eval behind Makefile + optional workflow
```bash
make test-agent-quality  # no-op when AGENTS_ENABLED unset
```

## Quality Gates

- [ ] pytest.ini exists with proper configuration
- [ ] Test discovery patterns configured
- [ ] Markers defined for test categories (including `agent_proof`, `quality`, `live_llm` when SAO §17 applies)
- [ ] Logging configured (file and console)
- [ ] Coverage reporting configured
- [ ] Makefile targets created for common operations (including `test-agent-proof` / `test-agent-quality` when agents enabled)
- [ ] All tests discoverable by pytest
- [ ] Tests organized in proper directory structure

## Test Organization

```
tests/
├── unit/                    # pytest -m unit
├── integration/             # pytest -m integration
│   └── agent/               # pytest -m agent_proof (lane 1)
├── e2e/                     # pytest -m e2e
├── fixtures/
│   ├── llm_scripts/         # CAP-004 ScriptedLLM queues per PRF-id
│   └── agent_tasks/         # TASK-* golden tasks (lane 4)
├── support/
│   ├── log_story.py
│   └── agent_story.py       # TFK-02 bootstrap
├── conftest.py              # Shared fixtures
└── pytest.ini               # Configuration
```

## Recommended pytest Plugins

```txt
# requirements.txt
pytest>=8.0.0
pytest-django>=4.5.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0
pytest-xdist>=3.3.0         # Parallel execution
pytest-timeout>=2.1.0       # Test timeouts
pytest-mock>=3.11.0         # Mocking support (unit tests only — not agent_proof)
```
