"""BSL Linter module.

Exports the ``BslLinter`` class and the ``lint`` convenience function.
"""
from __future__ import annotations

from bsl.linter.linter import BslLinter, lint
from bsl.linter.rules import ALL_LINT_RULES, COMPLETENESS_RULES, CONSISTENCY_RULES, NAMING_RULES

__all__ = [
    "BslLinter",
    "lint",
    "NAMING_RULES",
    "COMPLETENESS_RULES",
    "CONSISTENCY_RULES",
    "ALL_LINT_RULES",
]
