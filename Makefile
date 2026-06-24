.PHONY: up down logs build test test-local lint format migrate new-migration worker shell db-shell seed activate-component install install-hooks generate-tokens watch-css build-frontend smoke-test check-deps verify-tasks check-config pre-commit dev

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
	@echo "Installing pre-commit hooks..."
	@which pre-commit 2>/dev/null && pre-commit install && echo "Done." || echo "Install pre-commit: brew install pre-commit (macOS) or pipx install pre-commit"

watch-css: generate-tokens
	@tailwindcss -i app/static/tailwind.input.css -o app/static/app.css --watch

# ── Design tokens & frontend build ────────────────────────────────
# DESIGN_TOKENS.json is the single source of truth. Both frontends consume
# generated CSS custom properties; regenerate whenever the JSON changes.
generate-tokens:
	uv run python scripts/generate_tokens.py

build-frontend: generate-tokens
	cd frontend && npm run build

# ── Guard Rails ───────────────────────────────────────────────────

smoke-test:
	@echo "Starting smoke tests..."; bash scripts/smoke_test.sh

check-config:
	@bash scripts/check_config.sh

check-deps:
	@echo "Checking dependency resolution..."
	@python scripts/check_deps.py

verify-tasks:
	@echo "Verifying task registration..."
	@python scripts/verify_tasks.py

pre-commit: lint test-local smoke-test check-deps verify-tasks check-config
	@echo "✅ All guard rails passed"
