#!/usr/bin/env python3
"""Verify every core application module imports without error.

Extracted from the former inline ``make check-deps`` recipe (which was not
valid Makefile syntax) so the whole Makefile parses. Behaviour and output are
unchanged.
"""

from __future__ import annotations

import importlib
import sys

MODULES = [
    "app.core.config",
    "app.core.db",
    "app.core.tasks",
    "app.core.auth",
    "app.core.security",
    "app.core.errors",
    "app.core.logging",
    "app.core.templates",
    "app.main",
]


def main() -> None:
    errors: list[str] = []
    for mod_name in MODULES:
        try:
            importlib.import_module(mod_name)
            print(f"  \u2713 {mod_name}")
        except Exception as e:  # noqa: BLE001 — report any import failure
            errors.append(f"{mod_name}: {e}")
            print(f"  \u2717 {mod_name}: {e}")
    if errors:
        sys.exit(1)
    print("\n\u2705 All modules resolved")


if __name__ == "__main__":
    main()
