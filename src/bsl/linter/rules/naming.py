"""Naming convention lint rules for BSL.

These rules enforce consistent naming conventions across all BSL
identifiers (agent names, behavior names, invariant names).

Conventions enforced:
    - Agent names: UpperCamelCase (PascalCase)
    - Behavior names: lower_snake_case
    - Invariant names: lower_snake_case

Rule codes:
    LINT-N001  Agent name not PascalCase
    LINT-N002  Behavior name not snake_case
    LINT-N003  Invariant name not snake_case
    LINT-N004  Behavior name too short (< 3 characters)
    LINT-N005  Behavior name too generic (matches a blocklist)
"""
from __future__ import annotations

import re

from bsl.ast.nodes import AgentSpec
from bsl.validator.diagnostics import Diagnostic, DiagnosticSeverity

_PASCAL_CASE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
_SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")
_GENERIC_NAMES = frozenset({"do", "run", "execute", "process", "handle", "action", "task"})


def _diag(
    code: str,
    severity: DiagnosticSeverity,
    message: str,
    span: object,
    suggestion: str | None = None,
) -> Diagnostic:
    from bsl.ast.nodes import Span

    s: Span = span  # type: ignore[assignment]
    return Diagnostic(
        severity=severity,
        code=code,
        message=message,
        span=s,
        suggestion=suggestion,
        rule="naming",
    )


def rule_agent_name_pascal_case(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-N001: Agent names should be PascalCase."""
    if not _PASCAL_CASE.match(spec.name):
        return [_diag(
            "LINT-N001",
            DiagnosticSeverity.WARNING,
            f"Agent name {spec.name!r} should be PascalCase (e.g. 'CustomerServiceAgent')",
            spec.span,
            suggestion=f"Rename to '{spec.name.title().replace('_', '')}' or similar",
        )]
    return []


def rule_behavior_name_snake_case(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-N002: Behavior names should be snake_case."""
    diagnostics: list[Diagnostic] = []
    for behavior in spec.behaviors:
        if not _SNAKE_CASE.match(behavior.name):
            diagnostics.append(_diag(
                "LINT-N002",
                DiagnosticSeverity.WARNING,
                f"Behavior name {behavior.name!r} should be snake_case",
                behavior.span,
                suggestion=f"Rename to '{behavior.name.lower().replace('-', '_')}'",
            ))
    return diagnostics


def rule_invariant_name_snake_case(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-N003: Invariant names should be snake_case."""
    diagnostics: list[Diagnostic] = []
    for invariant in spec.invariants:
        if not _SNAKE_CASE.match(invariant.name):
            diagnostics.append(_diag(
                "LINT-N003",
                DiagnosticSeverity.WARNING,
                f"Invariant name {invariant.name!r} should be snake_case",
                invariant.span,
                suggestion=f"Rename to '{invariant.name.lower().replace('-', '_')}'",
            ))
    return diagnostics


def rule_behavior_name_length(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-N004: Behavior names should be descriptive (at least 3 characters)."""
    diagnostics: list[Diagnostic] = []
    for behavior in spec.behaviors:
        if len(behavior.name) < 3:
            diagnostics.append(_diag(
                "LINT-N004",
                DiagnosticSeverity.HINT,
                f"Behavior name {behavior.name!r} is very short; use a descriptive name",
                behavior.span,
                suggestion="Use a descriptive name that communicates the behavior's purpose",
            ))
    return diagnostics


def rule_behavior_name_not_generic(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-N005: Behavior names should not be generic/meaningless words."""
    diagnostics: list[Diagnostic] = []
    for behavior in spec.behaviors:
        if behavior.name.lower() in _GENERIC_NAMES:
            diagnostics.append(_diag(
                "LINT-N005",
                DiagnosticSeverity.HINT,
                f"Behavior name {behavior.name!r} is too generic; choose a more specific name",
                behavior.span,
                suggestion="Use a name that captures the domain-specific intent",
            ))
    return diagnostics


NAMING_RULES = [
    rule_agent_name_pascal_case,
    rule_behavior_name_snake_case,
    rule_invariant_name_snake_case,
    rule_behavior_name_length,
    rule_behavior_name_not_generic,
]
