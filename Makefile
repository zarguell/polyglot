.PHONY: up down logs build test test-local lint format migrate new-migration worker shell db-shell seed activate-component install install-hooks watch-css smoke-test check-deps verify-tasks check-config pre-commit dev

# ── Docker ────────────────────────────────────────────────────────
up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

# ── Dev server (requires Postgres from ``up``) ────────────────────
dev:
	uvicorn app.main:app --reload --port 8000

# ── Testing (Postgres only — no SQLite) ───────────────────────────
# ``make test`` runs inside Docker against Postgres (CI path).
# ``make test-local`` runs locally against Docker Postgres on localhost.
# Start postgres first: ``docker compose up -d postgres``
test:
	docker compose --profile ci run --rm test

test-local:
	pytest

test-coverage:
	pytest --cov=app --cov-report=term-missing

# ── Lint & Format ────────────────────────────────────────────────
lint:
	ruff check .
	basedpyright

format:
	ruff format .

# ── Database ──────────────────────────────────────────────────────
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

install-hooks:
	cp .pre-commit-config.yaml .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "Pre-commit hooks installed."

watch-css:
	@tailwindcss -i app/static/tailwind.input.css -o app/static/app.css --watch

# ── Guard Rails ───────────────────────────────────────────────────

smoke-test:
	@echo "Starting smoke tests..."; bash scripts/smoke_test.sh

check-config:
	@bash scripts/check_config.sh

check-deps:
	@echo "Checking dependency resolution..."; \
	python -c "
import importlib, sys
errors = []
for mod_name in ['app.core.config', 'app.core.db', 'app.core.tasks',
                 'app.core.auth', 'app.core.security', 'app.core.errors',
                 'app.core.logging', 'app.core.templates', 'app.main']:
    try:
        importlib.import_module(mod_name)
        print(f'  \u2713 {mod_name}')
    except Exception as e:
        errors.append(f'{mod_name}: {e}')
        print(f'  \u2717 {mod_name}: {e}')
if errors:
    sys.exit(1)
else:
    print('\n\u2705 All modules resolved')
"

verify-tasks:
	@echo "Verifying task registration..."; \
	python -c "
import importlib, sys
errors = []
for task_mod in ['app.tasks', 'app.core.tasks']:
    try:
        importlib.import_module(task_mod)
        print(f'  \u2713 {task_mod}')
    except Exception as e:
        errors.append(f'{task_mod}: {e}')
        print(f'  \u2717 {task_mod}: {e}')
if errors:
    sys.exit(1)
else:
    print('\n\u2705 All tasks registered')
"

pre-commit: lint test-local smoke-test check-deps verify-tasks check-config
	@echo "✅ All guard rails passed"
