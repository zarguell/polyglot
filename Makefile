.PHONY: up down logs build test lint format migrate new-migration worker shell db-shell seed activate-component

# ── Docker ──
up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

# ── Development server (local) ──
dev:
	uvicorn app.main:app --reload --port 8000

# ── Testing ──
test:
	pytest

test-coverage:
	pytest --cov=app --cov-report=term-missing

test-unit:
	pytest tests/unit

test-integration:
	pytest tests/integration

# ── Lint & Format ──
lint:
	ruff check .
	basedpyright

format:
	ruff format .

# ── Database ──
migrate:
	alembic upgrade head

new-migration:
	@read -p "Migration message: " msg; alembic revision --autogenerate -m "$$msg"

# ── Worker (run locally) ──
worker:
	procrastinate --app app.core.tasks.task_app worker

# ── Shell ──
shell:
	python -c "from app.core.db import engine; print('DB engine ready:', engine)"

db-shell:
	docker compose exec postgres psql -U polyglot -d polyglot

# ── Utilities ──
seed:
	python scripts/seed_dev.py

activate-component:
	@bash scripts/activate_component.sh $(COMPONENT)

install:
	uv sync

watch-css:
	@tailwindcss -i app/static/tailwind.input.css -o app/static/app.css --watch
