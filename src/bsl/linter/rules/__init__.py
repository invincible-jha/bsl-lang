"""BSL linter rules sub-package.

Re-exports all built-in lint rule collections.
"""
from __future__ import annotations

from bsl.linter.rules.completeness import COMPLETENESS_RULES
from bsl.linter.rules.consistency import CONSISTENCY_RULES
from bsl.linter.rules.naming import NAMING_RULES

ALL_LINT_RULES = [*NAMING_RULES, *COMPLETENESS_RULES, *CONSISTENCY_RULES]

__all__ = [
    "NAMING_RULES",
    "COMPLETENESS_RULES",
    "CONSISTENCY_RULES",
    "ALL_LINT_RULES",
]
