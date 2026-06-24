# Django Upgrade Component — Activation Guide

## What This Component Adds

This is a **documentation and tooling only** template. It does not install any code into `app/components/`. Instead, it provides:

- `docs/MIGRATION_GUIDE.md` — comprehensive Django migration guide for Polyglot applications
- `scripts/migrate_to_django.py` — analysis script that scans current app state and generates a migration report

## When to Use This Template

Activate this template when your Polyglot application has grown to a scale where Django's built-in ecosystem (admin UI, ORM richness, ecosystem packages) provides clear advantages over the FastAPI + SQLAlchemy stack.

## Activation

This template is documentation-only. To "activate" it:

```bash
# Copy the migration guide into your project docs
cp boilerplate/templates/django_upgrade/docs/MIGRATION_GUIDE.md docs/

# Copy the analysis script
cp boilerplate/templates/django_upgrade/scripts/migrate_to_django.py scripts/

# Run the analysis script to generate a migration report
python scripts/migrate_to_django.py
```

No environment variables, database tables, or Docker services are needed.

## Verification

```bash
# Run tests
pytest boilerplate/templates/django_upgrade/tests/test_django_upgrade.py -v
```
