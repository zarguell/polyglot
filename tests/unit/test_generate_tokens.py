"""Unit tests for the design-token CSS generator.

The generator is the single bridge between ``DESIGN_TOKENS.json`` (source of
truth) and the two frontends. These tests lock its output shape so a refactor
can never silently drift the emitted CSS custom properties.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

# Load the standalone script (scripts/ is not a package) by file path so the
# test does not depend on sys.path manipulation or packaging.
_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "generate_tokens.py"
_spec = importlib.util.spec_from_file_location("generate_tokens", _SCRIPT)
assert _spec is not None and _spec.loader is not None
generate_tokens = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(generate_tokens)


def _write_tokens(tmp_path: Path, appearance: dict[str, object]) -> Path:
    """Write a minimal DESIGN_TOKENS.json with the given appearance block."""
    path = tmp_path / "DESIGN_TOKENS.json"
    path.write_text(json.dumps({"appearance": appearance}))
    return path


# ── load_tokens ─────────────────────────────────────────────────────────


def test_load_tokens_returns_every_mapped_value_when_json_complete(tmp_path: Path) -> None:
    """Given a complete appearance block, load_tokens returns all mapped values."""
    # Given
    tokens_file = _write_tokens(
        tmp_path,
        {
            "primary_color": "#2563eb",
            "primary_hover": "#1d4ed8",
            "surface": "#ffffff",
            "surface_secondary": "#f9fafb",
            "border": "#e5e7eb",
            "text": "#111827",
            "text_secondary": "#6b7280",
            "font_family": "system-ui, -apple-system, sans-serif",
            "border_radius": "0.5rem",
            "density": "normal",
            "dark_mode_supported": True,
        },
    )

    # When
    tokens = generate_tokens.load_tokens(tokens_file)

    # Then — every CSS token key is present with its JSON value.
    assert tokens["primary_color"] == "#2563eb"
    assert tokens["text"] == "#111827"
    assert tokens["font_family"] == "system-ui, -apple-system, sans-serif"
    assert tokens["border_radius"] == "0.5rem"
    assert len(tokens) == 9


def test_load_tokens_raises_key_error_when_a_token_key_is_missing(tmp_path: Path) -> None:
    """Given a missing required key, load_tokens raises KeyError naming the key."""
    # Given — appearance missing "text"
    tokens_file = _write_tokens(
        tmp_path,
        {
            "primary_color": "#2563eb",
            "primary_hover": "#1d4ed8",
            "surface": "#ffffff",
            "surface_secondary": "#f9fafb",
            "border": "#e5e7eb",
            "text_secondary": "#6b7280",
            "font_family": "system-ui, sans-serif",
            "border_radius": "0.5rem",
        },
    )

    # When / Then
    with pytest.raises(KeyError, match="text"):
        generate_tokens.load_tokens(tokens_file)


def test_load_tokens_raises_type_error_when_value_is_not_a_string(tmp_path: Path) -> None:
    """Given a non-string token value, load_tokens raises TypeError."""
    # Given — border_radius is a number, not a CSS string
    tokens_file = _write_tokens(
        tmp_path,
        {
            "primary_color": "#2563eb",
            "primary_hover": "#1d4ed8",
            "surface": "#ffffff",
            "surface_secondary": "#f9fafb",
            "border": "#e5e7eb",
            "text": "#111827",
            "text_secondary": "#6b7280",
            "font_family": "system-ui, sans-serif",
            "border_radius": 0.5,
        },
    )

    # When / Then
    with pytest.raises(TypeError, match="border_radius"):
        generate_tokens.load_tokens(tokens_file)


# ── render_htmx ─────────────────────────────────────────────────────────


def test_render_htmx_emits_canonical_custom_properties(tmp_path: Path) -> None:
    """Given loaded tokens, render_htmx emits a :root block with the HTMX names."""
    # Given
    tokens_file = _write_tokens(
        tmp_path,
        {
            "primary_color": "#2563eb",
            "primary_hover": "#1d4ed8",
            "surface": "#ffffff",
            "surface_secondary": "#f9fafb",
            "border": "#e5e7eb",
            "text": "#111827",
            "text_secondary": "#6b7280",
            "font_family": "system-ui, -apple-system, sans-serif",
            "border_radius": "0.5rem",
        },
    )
    tokens = generate_tokens.load_tokens(tokens_file)

    # When
    css = generate_tokens.render_htmx(tokens)

    # Then — exact HTMX :root custom properties (matches the former hardcoded block).
    assert css.startswith(":root {")
    assert "  --color-primary: #2563eb;" in css
    assert "  --color-primary-hover: #1d4ed8;" in css
    assert "  --color-surface: #ffffff;" in css
    assert "  --color-surface-secondary: #f9fafb;" in css
    assert "  --color-border: #e5e7eb;" in css
    assert "  --color-text: #111827;" in css
    assert "  --color-text-secondary: #6b7280;" in css
    assert "  --font-family: system-ui, -apple-system, sans-serif;" in css
    assert "  --border-radius: 0.5rem;" in css
    assert css.rstrip().endswith("}")


# ── render_react ────────────────────────────────────────────────────────


def test_render_react_emits_tailwind_namespace_variables(tmp_path: Path) -> None:
    """Given loaded tokens, render_react emits a @theme block with Tailwind v4 names."""
    # Given
    tokens_file = _write_tokens(
        tmp_path,
        {
            "primary_color": "#2563eb",
            "primary_hover": "#1d4ed8",
            "surface": "#ffffff",
            "surface_secondary": "#f9fafb",
            "border": "#e5e7eb",
            "text": "#111827",
            "text_secondary": "#6b7280",
            "font_family": "system-ui, -apple-system, sans-serif",
            "border_radius": "0.5rem",
        },
    )
    tokens = generate_tokens.load_tokens(tokens_file)

    # When
    css = generate_tokens.render_react(tokens)

    # Then — React @theme uses Tailwind v4 namespaces and the frontend's names.
    assert css.startswith("@theme {")
    assert "  --color-primary: #2563eb;" in css
    assert "  --color-primary-hover: #1d4ed8;" in css
    assert "  --color-surface: #ffffff;" in css
    assert "  --color-surface-secondary: #f9fafb;" in css
    assert "  --color-border: #e5e7eb;" in css
    # text maps to the React-specific --color-text-primary name.
    assert "  --color-text-primary: #111827;" in css
    assert "  --color-text-secondary: #6b7280;" in css
    assert "  --font-family-sans: system-ui, -apple-system, sans-serif;" in css
    assert "  --radius-lg: 0.5rem;" in css
    # The React-specific alias names must NOT leak the HTMX names.
    assert "--color-text:" not in css
    assert "--font-family:" not in css
    assert "--border-radius:" not in css


def test_render_htmx_and_react_share_identical_values(tmp_path: Path) -> None:
    """Given the same tokens, both projections carry identical colour values."""
    # Given
    tokens_file = _write_tokens(
        tmp_path,
        {
            "primary_color": "#2563eb",
            "primary_hover": "#1d4ed8",
            "surface": "#ffffff",
            "surface_secondary": "#f9fafb",
            "border": "#e5e7eb",
            "text": "#111827",
            "text_secondary": "#6b7280",
            "font_family": "system-ui, sans-serif",
            "border_radius": "0.5rem",
        },
    )
    tokens = generate_tokens.load_tokens(tokens_file)

    # When
    htmx = generate_tokens.render_htmx(tokens)
    react = generate_tokens.render_react(tokens)

    # Then — every hex value appears in both projections (single source of truth).
    for value in ("#2563eb", "#1d4ed8", "#ffffff", "#f9fafb", "#e5e7eb", "#111827", "#6b7280"):
        assert value in htmx
        assert value in react
