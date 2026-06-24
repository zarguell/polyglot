#!/usr/bin/env python3
"""Django Migration Analysis Script.

Scans the current Polyglot application and generates a report showing what
would need to change for a Django migration. Run this to assess migration
complexity before committing.

Usage:
    python scripts/migrate_to_django.py
    python scripts/migrate_to_django.py --output report.md
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path


def scan_models(app_dir: Path) -> list[dict]:
    """Scan SQLAlchemy models and report their Django equivalents."""
    models_dir = app_dir / "models"
    if not models_dir.exists():
        return []

    results = []
    for py_file in sorted(models_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue

        content = py_file.read_text()
        classes = _extract_model_classes(content)
        for cls in classes:
            results.append(
                {
                    "file": str(py_file.relative_to(app_dir)),
                    "class": cls["name"],
                    "tablename": cls["tablename"],
                    "fields": len(cls["fields"]),
                    "django_equivalent": f'django.db.models.Model (app_label="{cls["tablename"].split("_")[0] if "_" in cls["tablename"] else "core"}")',
                }
            )

    return results


def scan_api_routes(app_dir: Path) -> list[dict]:
    """Scan FastAPI routes and report their Django equivalents."""
    api_dir = app_dir / "api"
    if not api_dir.exists():
        return []

    results = []
    for py_file in sorted(api_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue

        content = py_file.read_text()
        routes = _extract_fastapi_routes(content)
        for route in routes:
            django_view = (
                "APIView"
                if route["method"] == "GET"
                else ("CreateAPIView" if route["method"] == "POST" else "GenericAPIView")
            )
            results.append(
                {
                    "file": str(py_file.relative_to(app_dir)),
                    "method": route["method"],
                    "path": route["path"],
                    "django_equivalent": f"DRF {django_view}",
                }
            )

    return results


def scan_tasks(app_dir: Path) -> list[dict]:
    """Scan Procrastinate tasks and report their Celery equivalents."""
    tasks_dir = app_dir / "tasks"
    if not tasks_dir.exists():
        return []

    results = []
    for py_file in sorted(tasks_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue

        content = py_file.read_text()
        task_names = _extract_task_names(content)
        for name in task_names:
            results.append(
                {
                    "file": str(py_file.relative_to(app_dir)),
                    "task": name,
                    "django_equivalent": "@shared_task (Celery/Django Q)",
                }
            )

    return results


def scan_templates(app_dir: Path) -> list[dict]:
    """Find Jinja2 templates and report their Django template equivalents."""
    templates_dir = app_dir / "templates"
    if not templates_dir.exists():
        return []

    results = []
    for tmpl in templates_dir.rglob("*.html"):
        results.append(
            {
                "file": str(tmpl.relative_to(app_dir)),
                "engine": "Jinja2",
                "django_equivalent": "Django Template Language",
            }
        )

    return results


def count_activated_components(boilerplate_dir: Path) -> int:
    """Count activated component packs for complexity assessment."""
    components_dir = boilerplate_dir.parent.parent / "app" / "components"
    if not components_dir.exists():
        return 0

    return len(list(components_dir.iterdir()))


def _extract_model_classes(content: str) -> list[dict]:
    """Naive parser for SQLAlchemy model classes."""
    classes = []
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("class ") and "(Base):" in line:
            name = line.split("class ")[1].split("(Base)")[0].strip()
            tablename = ""
            fields = []
            # Look ahead for __tablename__ and Mapped columns
            for j in range(i + 1, min(i + 50, len(lines))):
                look = lines[j].strip()
                if look.startswith("__tablename__"):
                    tablename = look.split('"')[1] if '"' in look else ""
                elif "Mapped[" in look:
                    fields.append(look.split(":")[0].strip())
                elif look.startswith("class ") and j > i + 5:
                    break

            classes.append(
                {
                    "name": name,
                    "tablename": tablename or name.lower(),
                    "fields": fields,
                }
            )
        i += 1
    return classes


def _extract_fastapi_routes(content: str) -> list[dict]:
    """Naive parser for FastAPI route decorators."""
    routes = []
    for line in content.split("\n"):
        line = line.strip()
        for method in [
            "@router.get",
            "@router.post",
            "@router.put",
            "@router.delete",
            "@router.patch",
        ]:
            if method in line:
                path = line.split('"')[1] if '"' in line else "/"
                routes.append(
                    {
                        "method": method.replace("@router.", "").upper(),
                        "path": path,
                    }
                )
    return routes


def _extract_task_names(content: str) -> list[str]:
    """Naive parser for Procrastinate task names."""
    tasks = []
    for line in content.split("\n"):
        if "task(name=" in line or 'task(name="' in line:
            name = line.split('"')[1] if '"' in line else "unknown"
            tasks.append(name)
    return tasks


def generate_report(app_dir: Path, boilerplate_dir: Path) -> str:
    """Generate a comprehensive migration report."""
    models = scan_models(app_dir)
    routes = scan_api_routes(app_dir)
    tasks = scan_tasks(app_dir)
    templates = scan_templates(app_dir)
    components = count_activated_components(boilerplate_dir)

    now = datetime.now().isoformat()

    lines = [
        "# Django Migration Analysis Report",
        f"Generated: {now}",
        "",
        "## Summary",
        "",
        f"- SQLAlchemy Models: {len(models)}",
        f"- FastAPI Routes: {len(routes)}",
        f"- Procrastinate Tasks: {len(tasks)}",
        f"- Jinja2 Templates: {len(templates)}",
        f"- Activated Components: {components}",
        "",
        "## Complexity Assessment",
        "",
    ]

    # Score complexity
    total_items = len(models) + len(routes) + len(tasks)
    if total_items == 0:
        level = "Trivial"
        desc = "No models, routes, or tasks detected. Migration is a greenfield Django project."
    elif total_items < 10:
        level = "Low"
        desc = "Small codebase. Migration can be completed in hours."
    elif total_items < 50:
        level = "Medium"
        desc = "Moderate codebase. Migration takes 1-3 days."
    else:
        level = "High"
        desc = "Large codebase. Plan for a phased migration over 1-2 weeks."

    lines.extend(
        [
            f"**Complexity Level: {level}**",
            "",
            f"{desc}",
            "",
            "---",
            "",
            "## SQLAlchemy Models → Django Models",
            "",
            "| File | Class | Table | Fields | Django Equivalent |",
            "|------|-------|-------|--------|-----------------|",
        ]
    )

    for m in models:
        lines.append(
            f"| {m['file']} | {m['class']} | {m['tablename']} | {m['fields']} | {m['django_equivalent']} |"
        )

    lines.extend(
        [
            "",
            "## FastAPI Routes → Django/DRF Views",
            "",
            "| File | Method | Path | Django Equivalent |",
            "|------|--------|------|-----------------|",
        ]
    )

    for r in routes:
        lines.append(f"| {r['file']} | {r['method']} | {r['path']} | {r['django_equivalent']} |")

    lines.extend(
        [
            "",
            "## Procrastinate Tasks → Celery/Django Q",
            "",
            "| File | Task | Django Equivalent |",
            "|------|------|-----------------|",
        ]
    )

    for t in tasks:
        lines.append(f"| {t['file']} | {t['task']} | {t['django_equivalent']} |")

    lines.extend(
        [
            "",
            "## Jinja2 Templates → Django Templates",
            "",
            "| File | Current Engine | Django Equivalent |",
            "|------|---------------|-----------------|",
        ]
    )

    for t in templates:
        lines.append(f"| {t['file']} | {t['engine']} | {t['django_equivalent']} |")

    lines.extend(
        [
            "",
            "## Next Steps",
            "",
            "1. Review `docs/MIGRATION_GUIDE.md` for the step-by-step migration path",
            "2. Start with models and migrations — they are the foundation",
            "3. Set up Django Admin for immediate CRUD access to all models",
            "4. Migrate API routes using Django REST Framework or Django Ninja",
            "5. Move tasks to Celery or Django Q",
            "6. Convert Jinja2 templates to Django templates last",
            "",
            "Consult the Polyglot Django Migration Guide (docs/MIGRATION_GUIDE.md) for details",
            "on each step, common pitfalls, and how the Polyglot architecture makes migration easier.",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    """Entry point — scan the app and print/generate a migration report."""
    # Determine project root from script location
    script_dir = Path(__file__).resolve().parent
    project_root = (
        script_dir.parent.parent.parent
    )  # scripts/ -> django_upgrade/ -> templates/ -> boilerplate/ -> root
    app_dir = project_root / "app"
    boilerplate_dir = project_root / "boilerplate"

    output_file = None
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "--output":
        output_file = args[1]

    print("== Polyglot → Django Migration Analysis ==")
    print(f"Project root: {project_root}")
    print()

    report = generate_report(app_dir, boilerplate_dir)

    if output_file:
        output_path = project_root / output_file
        output_path.write_text(report)
        print(f"Report written to {output_path}")
    else:
        print(report)


if __name__ == "__main__":
    main()
