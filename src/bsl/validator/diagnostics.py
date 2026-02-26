"""Diagnostic types for the BSL validator and linter.

A ``Diagnostic`` is an annotated message attached to a source location.
Diagnostics are produced by both the ``Validator`` (semantic checks) and
the ``BslLinter`` (style / quality checks).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from bsl.ast.nodes import Span


class DiagnosticSeverity(Enum):
    """Severity levels for diagnostics, aligned with LSP conventions."""

    ERROR = auto()
    WARNING = auto()
    INFORMATION = auto()
    HINT = auto()


@dataclass(frozen=True)
class Diagnostic:
    """A single validation or lint finding.

    Parameters
    ----------
    severity:
        How serious this finding is.
    code:
        A short machine-readable identifier, e.g. ``"BSL001"``.
    message:
        Human-readable description of the problem.
    span:
        Source location of the offending code.
    suggestion:
        Optional human-readable fix suggestion.
    rule:
        The rule name that produced this diagnostic.
    """

    severity: DiagnosticSeverity
    code: str
    message: str
    span: Span
    suggestion: str | None = field(default=None)
    rule: str = field(default="")

    def __str__(self) -> str:
        loc = f"{self.span.line}:{self.span.col}"
        prefix = f"[{self.code}] {self.severity.name}"
        suggestion_part = f" (hint: {self.suggestion})" if self.suggestion else ""
        return f"{prefix} at {loc}: {self.message}{suggestion_part}"

    @property
    def is_error(self) -> bool:
        """Return True if this diagnostic should block a successful validation."""
        return self.severity == DiagnosticSeverity.ERROR
