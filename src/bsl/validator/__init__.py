"""BSL Validator module.

Exports the ``Validator`` class, the ``validate`` convenience function,
``Diagnostic`` types, and all built-in validation rules.
"""
from __future__ import annotations

from bsl.validator.diagnostics import Diagnostic, DiagnosticSeverity
from bsl.validator.rules import DEFAULT_RULES, Rule
from bsl.validator.validator import Validator, validate

__all__ = [
    "Validator",
    "validate",
    "Diagnostic",
    "DiagnosticSeverity",
    "Rule",
    "DEFAULT_RULES",
]
