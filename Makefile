.PHONY: up down logs build test lint format migrate new-migration worker shell db-shell seed activate-component install watch-css smoke-test check-deps verify-tasks dev

# ── Docker (REQUIRED for all development) ──────────────────────────
# Do NOT run ``pytest``, ``alembic``, or ``uvicorn`` outside Docker.
# Use ``make dev`` for local development (runs all backing services).

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

# ── Development server (local, requires ``up`` for Postgres) ──────
dev:
	uvicorn app.main:app --reload --port 8000

# ── Testing (runs against Postgres in Docker) ─────────────────────
test:
	pytest

test-coverage:
	pytest --cov=app --cov-report=term-missing

test-unit:
	pytest tests/unit

test-integration:
	pytest tests/integration

# ── Lint & Format ────────────────────────────────────────────────
lint:
	ruff check .
	basedpyright

format:
	ruff format .

# ── Database (requires ``up``) ────────────────────────────────────
migrate:
	alembic upgrade head

new-migration:
	@read -p "Migration message: " msg; alembic revision --autogenerate -m "$$msg"

# ── Worker ────────────────────────────────────────────────────────
worker:
	procrastinate --app app.core.tasks.task_app worker

# ── Shell ─────────────────────────────────────────────────────────
shell:
	python -c "from app.core.db import engine; print('DB engine ready:', engine)"

db-shell:
	docker compose exec postgres psql -U polyglot -d polyglot

# ── Utilities ─────────────────────────────────────────────────────
seed:
	python scripts/seed_dev.py

activate-component:
	@bash scripts/activate_component.sh $(COMPONENT)

install:
	uv sync

watch-css:
	@tailwindcss -i app/static/tailwind.input.css -o app/static/app.css --watch

# ── Guard Rails (machine-enforced conventions) ────────────────────

# smoke-test: verify the app boots, pages render, and security headers are present.
# Run BEFORE every commit. Fails if the server isn't running.
smoke-test:
	@echo "Starting smoke tests..."
	@bash scripts/smoke_test.sh

# check-deps: verify all dependencies resolve by importing every app module.
# Catches missing transitive deps (aiopg, psycopg-binary, etc.).
check-deps:
	@echo "Checking dependency resolution..."
	@python -c "
import importlib, pkgutil, sys
errors = []
# Import all top-level app modules
for mod_name in ['app.core.config', 'app.core.db', 'app.core.tasks',
                 'app.core.auth', 'app.core.security', 'app.core.errors',
                 'app.core.logging', 'app.core.templates', 'app.main']:
    try:
        importlib.import_module(mod_name)
        print(f'  ✓ {mod_name}')
    except Exception as e:
        errors.append(f'{mod_name}: {e}')
        print(f'  ✗ {mod_name}: {e}')
if errors:
    print(f'\n❌ {len(errors)} module(s) failed to import')
    sys.exit(1)
else:
    print('\n✅ All modules resolved')
"

# verify-tasks: import all task modules to check for registration errors.
# Catches Procrastinate API drift (e.g., periodic() syntax changes).
verify-tasks:
	@echo "Verifying task registration..."
	@python -c "
import importlib, sys
errors = []
for task_mod in ['app.tasks', 'app.core.tasks']:
    try:
        importlib.import_module(task_mod)
        print(f'  ✓ {task_mod}')
    except Exception as e:
        errors.append(f'{task_mod}: {e}')
        print(f'  ✗ {task_mod}: {e}')
if errors:
    print(f'\n❌ Task registration failed')
    sys.exit(1)
else:
    print('\n✅ All tasks registered')
"

# pre-commit: run ALL guard rails. Execute before every push.
pre-commit: lint test smoke-test check-deps verify-tasks
	@echo "✅ All guard rails passed"
