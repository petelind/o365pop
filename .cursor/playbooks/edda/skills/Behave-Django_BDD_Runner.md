# Behave-Django BDD Runner

**Capability**: BDD Test Execution
**Stack**: behave, django, behave-django

# Skill: Behave-Django BDD Runner

**Capability Domain**: BDD_RUNNER
**Technology Stack**: behave+Django+Playwright

## Overview

Patterns for running BDD acceptance and E2E tests using behave-django. AT uses Django test client under `docs/features/`. E2E uses Playwright + LiveServer under `tests/e2e/`. Same Gherkin phrases; separate step libraries and `environment.py` files.

## Reference Implementation

### Pattern 1: behave.ini Configuration

```ini
[behave]
paths = docs/features
format = pretty
logging_level = INFO
tags = ~@wip
stdout_capture = false
stderr_capture = false
log_capture = false
```

Makefile: `make test-at` → `docs/features/`; `make test-e2e` → `tests/e2e/` (overrides path).

### Pattern 2: environment.py Lifecycle (Acceptance Tests)

```python
# docs/features/environment.py
import django
from django.test.utils import setup_test_environment, teardown_test_environment
from django.core.management import call_command

def before_all(context):
    django.setup()
    setup_test_environment()
    call_command('loaddata', 'tests/fixtures/seed.json')

def before_scenario(context, scenario):
    from django.test import TestCase
    context._test = TestCase('__init__')
    context._test._pre_setup()

def after_scenario(context, scenario):
    context._test._post_teardown()

def after_all(context):
    teardown_test_environment()
```

### Pattern 3: environment.py Lifecycle (E2E Tests with Playwright)

```python
# tests/e2e/environment.py
# Playwright browser, LiveServerTestCase, base_url targeting, screenshot-on-step.
```

AT is not LiveServer. LiveServer belongs to E2E only.

### Pattern 4: E2E Session Auth (Django + Playwright)

**Problem:** Hand-rolling `SessionStore` keys or skipping auth causes Playwright requests to hit the app as anonymous — steps time out looking for authenticated UI.

**Solution:** Create the user in the test DB, authenticate via Django's test `Client`, copy the `sessionid` cookie into Playwright before navigation.

```python
from django.test import Client

def force_login_playwright(context, user, live_server_url: str) -> None:
    """Inject Django session cookie so Playwright requests are authenticated."""
    client = Client()
    client.force_login(user)
    client.get("/")  # materialize session
    session_key = client.cookies["sessionid"].value
    base = live_server_url.rstrip("/")
    context.page.goto(base + "/")
    context.page.context.add_cookies(
        [
            {
                "name": "sessionid",
                "value": session_key,
                "domain": "localhost",
                "path": "/",
            }
        ]
    )
```

**Do not:** construct session keys manually; assume login UI exists when AT/E2E can seed users via factories.

**When:** any E2E step that needs an authenticated browser session on a Django app using session middleware.

### Pattern 5: Idempotent behave Fixture Givens

**Problem:** A `Background:` block and a scenario-specific `Given` both `create()` entities with the same natural key (slug, username, unique together) → `IntegrityError` on the second insert.

**Solution:** In step definitions that seed data, use `get_or_create` or update-in-place when the natural key is stable across Background + scenario.

```python
from behave import given

@given('the tenant "{slug}" exists')
def step_tenant_exists(context, slug):
    obj, created = Tenant.objects.get_or_create(
        slug=slug,
        defaults={"name": slug.title()},
    )
    if not created:
        obj.name = slug.title()
        obj.save(update_fields=["name"])
```

**Rule:** If Background already seeds entity X, scenario Givens that touch X must be idempotent — not blind `create()`.

**When:** any behave feature with shared Background + per-scenario data setup.
