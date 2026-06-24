#!/usr/bin/env python3
"""Verify Procrastinate task modules register without error.

Extracted from the former inline ``make verify-tasks`` recipe (which was not
valid Makefile syntax) so the whole Makefile parses. Behaviour and output are
unchanged.
"""

from __future__ import annotations

import importlib
import sys

TASK_MODULES = [
    "app.tasks",
    "app.core.tasks",
]


def main() -> None:
    errors: list[str] = []
    for task_mod in TASK_MODULES:
        try:
            importlib.import_module(task_mod)
            print(f"  \u2713 {task_mod}")
        except Exception as e:  # noqa: BLE001 — report any registration failure
            errors.append(f"{task_mod}: {e}")
            print(f"  \u2717 {task_mod}: {e}")
    if errors:
        sys.exit(1)
    print("\n\u2705 All tasks registered")


if __name__ == "__main__":
    main()
