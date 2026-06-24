"""Unit tests for Django Upgrade template."""

from __future__ import annotations

from pathlib import Path


def test_migration_guide_exists():
    """MIGRATION_GUIDE.md exists and contains expected sections."""
    template_dir = Path(__file__).resolve().parent.parent
    guide_path = template_dir / "docs" / "MIGRATION_GUIDE.md"
    assert guide_path.is_file(), f"MIGRATION_GUIDE.md not found at {guide_path}"

    content = guide_path.read_text()
    assert "When to Migrate" in content or "When to migrate" in content
    assert "Complexity Ladder" in content or "complexity ladder" in content
    assert "Django Model" in content or "Django model" in content
    assert "FastAPI route" in content or "FastAPI Route" in content
    assert "Step-by-Step" in content or "step-by-step" in content


def test_migrate_script_exists():
    """migrate_to_django.py exists and is a Python file."""
    template_dir = Path(__file__).resolve().parent.parent
    script_path = template_dir / "scripts" / "migrate_to_django.py"
    assert script_path.is_file(), f"migrate_to_django.py not found at {script_path}"


def test_migrate_script_is_valid_python():
    """migrate_to_django.py at minimum imports without syntax errors."""
    import importlib.util
    import sys

    template_dir = Path(__file__).resolve().parent.parent
    script_path = template_dir / "scripts" / "migrate_to_django.py"

    spec = importlib.util.spec_from_file_location("migrate_to_django", str(script_path))
    assert spec is not None, "Could not create module spec"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["migrate_to_django"] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        # Script may raise SystemExit when run standalone — that's fine
        if not isinstance(exc, SystemExit) and not isinstance(exc, ImportError):
            raise


def test_activate_md_exists():
    """ACTIVATE.md exists in the template directory."""
    template_dir = Path(__file__).resolve().parent.parent
    activate_path = template_dir / "ACTIVATE.md"
    assert activate_path.is_file(), f"ACTIVATE.md not found at {activate_path}"


def test_env_additions_exists():
    """env.additions exists in the template directory."""
    template_dir = Path(__file__).resolve().parent.parent
    env_path = template_dir / "env.additions"
    assert env_path.is_file(), f"env.additions not found at {env_path}"
