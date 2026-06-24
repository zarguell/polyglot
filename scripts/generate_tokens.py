#!/usr/bin/env python3
"""Generate CSS custom properties from ``DESIGN_TOKENS.json``.

``DESIGN_TOKENS.json`` (repo root) is the single source of truth for design
tokens. This script reads it and emits two CSS projections so both frontends
consume generated output instead of hardcoding duplicate values:

* ``app/static/generated/tokens.css`` — a ``:root`` block imported by the
  HTMX/Jinja2 Tailwind v3 input (``app/static/tailwind.input.css``).
* ``frontend/src/styles/tokens.generated.css`` — a Tailwind v4 ``@theme`` block
  imported by the React Vite entry (``frontend/src/styles/index.css``).

The two frontends use different naming conventions, so each projection maps the
same JSON values into its own variable names. Editing the JSON and running
``make generate-tokens`` (or this script directly) propagates to both.

Standard library only — no third-party dependencies.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent
TOKENS_JSON = REPO_ROOT / "DESIGN_TOKENS.json"
HTMX_OUTPUT = REPO_ROOT / "app" / "static" / "generated" / "tokens.css"
REACT_OUTPUT = REPO_ROOT / "frontend" / "src" / "styles" / "tokens.generated.css"

_HEADER = """\
/*
 * GENERATED — DO NOT EDIT BY HAND.
 * Source of truth: DESIGN_TOKENS.json
 * Regenerate: `make generate-tokens` (or `uv run python scripts/generate_tokens.py`)
 */
"""


class TokenSpec(NamedTuple):
    """One design token: the JSON key and its CSS variable name per frontend."""

    json_key: str
    htmx_var: str
    react_var: str


# Ordered mapping: appearance key -> (HTMX :root variable, React @theme variable).
# Order is deliberate and stable so generated output diffs are minimal.
TOKENS: list[TokenSpec] = [
    TokenSpec("primary_color", "--color-primary", "--color-primary"),
    TokenSpec("primary_hover", "--color-primary-hover", "--color-primary-hover"),
    TokenSpec("surface", "--color-surface", "--color-surface"),
    TokenSpec("surface_secondary", "--color-surface-secondary", "--color-surface-secondary"),
    TokenSpec("border", "--color-border", "--color-border"),
    TokenSpec("text", "--color-text", "--color-text-primary"),
    TokenSpec("text_secondary", "--color-text-secondary", "--color-text-secondary"),
    TokenSpec("font_family", "--font-family", "--font-family-sans"),
    TokenSpec("border_radius", "--border-radius", "--radius-lg"),
]


def load_tokens(path: Path = TOKENS_JSON) -> dict[str, str]:
    """Parse ``DESIGN_TOKENS.json`` and return ``{json_key: value}`` for CSS tokens.

    Raises:
        KeyError: if the appearance block is missing a required token key.
        TypeError: if a token value is not a string.
    """
    appearance: dict[str, object] = json.loads(path.read_text())["appearance"]
    tokens: dict[str, str] = {}
    for spec in TOKENS:
        if spec.json_key not in appearance:
            raise KeyError(f"DESIGN_TOKENS.json missing required token: appearance.{spec.json_key}")
        value = appearance[spec.json_key]
        if not isinstance(value, str):
            raise TypeError(
                f"DESIGN_TOKENS.json appearance.{spec.json_key} must be a string, "
                f"got {type(value).__name__}"
            )
        tokens[spec.json_key] = value
    return tokens


def render_htmx(tokens: dict[str, str]) -> str:
    """Render the HTMX ``:root`` block from loaded tokens."""
    lines = [":root {"]
    lines.extend(f"  {spec.htmx_var}: {tokens[spec.json_key]};" for spec in TOKENS)
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_react(tokens: dict[str, str]) -> str:
    """Render the React Tailwind v4 ``@theme`` block from loaded tokens."""
    lines = ["@theme {"]
    lines.extend(f"  {spec.react_var}: {tokens[spec.json_key]};" for spec in TOKENS)
    lines.append("}")
    return "\n".join(lines) + "\n"


def generate(
    tokens_json: Path = TOKENS_JSON,
    htmx_output: Path = HTMX_OUTPUT,
    react_output: Path = REACT_OUTPUT,
) -> tuple[Path, Path]:
    """Generate both CSS projection files and return their paths."""
    tokens = load_tokens(tokens_json)
    htmx_output.parent.mkdir(parents=True, exist_ok=True)
    react_output.parent.mkdir(parents=True, exist_ok=True)
    htmx_output.write_text(_HEADER + render_htmx(tokens))
    react_output.write_text(_HEADER + render_react(tokens))
    return htmx_output, react_output


def main() -> None:
    """CLI entry point: generate both files and report their paths."""
    htmx, react = generate()
    print(f"\u2713 HTMX tokens  -> {htmx.relative_to(REPO_ROOT)}")
    print(f"\u2713 React tokens -> {react.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
