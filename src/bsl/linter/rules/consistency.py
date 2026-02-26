"""Cross-behavior consistency lint rules for BSL.

These rules detect inconsistencies across multiple behaviors within
the same agent, such as behaviors that share should-constraints with
wildly different percentages, or behaviors that lack escalation when
others define it.

Rule codes:
    LINT-X001  Should-constraint percentages inconsistent across behaviors
    LINT-X002  Some behaviors define escalation, others do not
    LINT-X003  Behaviors reference overlapping must/should constraints (possible duplication)
    LINT-X004  Multiple behaviors with identical when-clauses
    LINT-X005  Model metadata references deprecated model names
"""
from __future__ import annotations

from collections import defaultdict

from bsl.ast.nodes import AgentSpec, Expression, Identifier, DotAccess, StringLit, NumberLit, BoolLit
from bsl.validator.diagnostics import Diagnostic, DiagnosticSeverity

_DEPRECATED_MODELS = frozenset({"gpt-3", "gpt-3.5-turbo", "text-davinci-003", "claude-1", "claude-2"})


def _expr_str(expr: Expression) -> str:
    if isinstance(expr, Identifier):
        return expr.name
    if isinstance(expr, DotAccess):
        return ".".join(expr.parts)
    if isinstance(expr, StringLit):
        return f'"{expr.value}"'
    if isinstance(expr, NumberLit):
        return str(expr.value)
    if isinstance(expr, BoolLit):
        return str(expr.value).lower()
    return repr(expr)


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
        rule="consistency",
    )


def rule_consistent_should_percentages(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-X001: Should-constraint percentages should be consistent across behaviors."""
    diagnostics: list[Diagnostic] = []
    # Group by expression string, collect percentages across behaviors
    expr_percentages: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for behavior in spec.behaviors:
        for should in behavior.should_constraints:
            if should.percentage is not None:
                key = _expr_str(should.expression)
                expr_percentages[key].append((behavior.name, should.percentage))

    for expr_key, entries in expr_percentages.items():
        if len(entries) > 1:
            percentages = {pct for _, pct in entries}
            if len(percentages) > 1:
                behavior_names = ", ".join(f"{name}({pct}%)" for name, pct in entries)
                diagnostics.append(_diag(
                    "LINT-X001",
                    DiagnosticSeverity.HINT,
                    f"Expression {expr_key!r} has different should-percentages across behaviors: "
                    f"{behavior_names}",
                    spec.span,
                    suggestion="Unify the percentage thresholds or use an invariant",
                ))
    return diagnostics


def rule_consistent_escalation(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-X002: If any behavior defines escalation, all should consider it."""
    diagnostics: list[Diagnostic] = []
    if len(spec.behaviors) < 2:
        return diagnostics

    has_escalation = [b for b in spec.behaviors if b.escalation is not None]
    no_escalation = [b for b in spec.behaviors if b.escalation is None]

    if has_escalation and no_escalation:
        without_names = ", ".join(b.name for b in no_escalation[:3])
        if len(no_escalation) > 3:
            without_names += f" (+{len(no_escalation) - 3} more)"
        diagnostics.append(_diag(
            "LINT-X002",
            DiagnosticSeverity.HINT,
            f"Some behaviors define escalation_to_human, but {without_names} do not",
            spec.span,
            suggestion="Consider adding escalation clauses to all behaviors, or use an invariant",
        ))
    return diagnostics


def rule_no_duplicate_must_across_behaviors(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-X003: Identical must-constraints in multiple behaviors suggest duplication."""
    diagnostics: list[Diagnostic] = []
    # Map expression → list of behavior names that have it as a must constraint
    expr_behaviors: dict[str, list[str]] = defaultdict(list)
    for behavior in spec.behaviors:
        for c in behavior.must_constraints:
            key = _expr_str(c.expression)
            expr_behaviors[key].append(behavior.name)

    for expr_key, names in expr_behaviors.items():
        if len(names) > 2:
            names_str = ", ".join(names)
            diagnostics.append(_diag(
                "LINT-X003",
                DiagnosticSeverity.HINT,
                f"Must-constraint {expr_key!r} appears in {len(names)} behaviors ({names_str}); "
                "consider moving it to an invariant",
                spec.span,
                suggestion="Extract shared must-constraints into an invariant with applies_to: all_behaviors",
            ))
    return diagnostics


def rule_unique_when_clauses(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-X004: Multiple behaviors with identical when-clauses may overlap."""
    diagnostics: list[Diagnostic] = []
    when_map: dict[str, list[str]] = defaultdict(list)
    for behavior in spec.behaviors:
        if behavior.when_clause is not None:
            key = _expr_str(behavior.when_clause)
            when_map[key].append(behavior.name)

    for when_key, names in when_map.items():
        if len(names) > 1:
            diagnostics.append(_diag(
                "LINT-X004",
                DiagnosticSeverity.WARNING,
                f"Behaviors {names} all have the same when-clause {when_key!r}; "
                "this may cause ambiguous routing",
                spec.span,
                suggestion="Ensure when-clauses are mutually exclusive or merge the behaviors",
            ))
    return diagnostics


def rule_no_deprecated_models(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-X005: Agents should not reference deprecated model versions."""
    diagnostics: list[Diagnostic] = []
    if spec.model is not None and spec.model.lower() in _DEPRECATED_MODELS:
        diagnostics.append(_diag(
            "LINT-X005",
            DiagnosticSeverity.WARNING,
            f"Agent {spec.name!r} references deprecated model {spec.model!r}",
            spec.span,
            suggestion="Upgrade to a current model version",
        ))
    return diagnostics


CONSISTENCY_RULES = [
    rule_consistent_should_percentages,
    rule_consistent_escalation,
    rule_no_duplicate_must_across_behaviors,
    rule_unique_when_clauses,
    rule_no_deprecated_models,
]
