"""Individual validation rules for the BSL validator.

Each rule is a callable that accepts an ``AgentSpec`` and returns a
list of ``Diagnostic`` objects.  Rules are composed into the
``Validator`` class which runs them all and aggregates results.

Rule codes use the ``BSL`` prefix followed by a three-digit number:

    BSL001  Duplicate behavior name
    BSL002  Duplicate invariant name
    BSL003  Undefined behavior referenced in applies_to
    BSL004  Percentage out of range (0–100)
    BSL005  Empty behavior (no constraints at all)
    BSL006  Missing model metadata
    BSL007  Missing version metadata
    BSL008  Conflict: same expression in must and must_not
    BSL009  Degradation references undefined behavior name
    BSL010  Threshold value out of valid range
"""
from __future__ import annotations

from collections import Counter
from typing import Callable

from bsl.ast.nodes import (
    AgentSpec,
    AppliesTo,
    BinaryOpExpr,
    BoolLit,
    Constraint,
    ContainsExpr,
    DotAccess,
    Expression,
    Identifier,
    InListExpr,
    NumberLit,
    ShouldConstraint,
    Span,
    StringLit,
)
from bsl.validator.diagnostics import Diagnostic, DiagnosticSeverity

Rule = Callable[[AgentSpec], list[Diagnostic]]


def _expr_to_str(expr: Expression) -> str:
    """Produce a canonical string representation of an expression for comparison."""
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
    if isinstance(expr, BinaryOpExpr):
        return f"({_expr_to_str(expr.left)} {expr.op.name} {_expr_to_str(expr.right)})"
    if isinstance(expr, ContainsExpr):
        return f"({_expr_to_str(expr.subject)} contains {_expr_to_str(expr.value)})"
    if isinstance(expr, InListExpr):
        items = ", ".join(_expr_to_str(i) for i in expr.items)
        return f"({_expr_to_str(expr.subject)} in [{items}])"
    return repr(expr)


def _make(
    code: str,
    severity: DiagnosticSeverity,
    message: str,
    span: Span,
    suggestion: str | None = None,
    rule: str = "",
) -> Diagnostic:
    return Diagnostic(
        severity=severity,
        code=code,
        message=message,
        span=span,
        suggestion=suggestion,
        rule=rule,
    )


# ---------------------------------------------------------------------------
# BSL001 — duplicate behavior names
# ---------------------------------------------------------------------------

def rule_duplicate_behaviors(spec: AgentSpec) -> list[Diagnostic]:
    """BSL001: Behavior names must be unique within an agent."""
    diagnostics: list[Diagnostic] = []
    seen: dict[str, Span] = {}
    for behavior in spec.behaviors:
        if behavior.name in seen:
            diagnostics.append(_make(
                "BSL001",
                DiagnosticSeverity.ERROR,
                f"Duplicate behavior name {behavior.name!r}; first defined at "
                f"{seen[behavior.name].line}:{seen[behavior.name].col}",
                behavior.span,
                suggestion=f"Rename one of the '{behavior.name}' behaviors",
                rule="duplicate_behaviors",
            ))
        else:
            seen[behavior.name] = behavior.span
    return diagnostics


# ---------------------------------------------------------------------------
# BSL002 — duplicate invariant names
# ---------------------------------------------------------------------------

def rule_duplicate_invariants(spec: AgentSpec) -> list[Diagnostic]:
    """BSL002: Invariant names must be unique within an agent."""
    diagnostics: list[Diagnostic] = []
    seen: dict[str, Span] = {}
    for invariant in spec.invariants:
        if invariant.name in seen:
            diagnostics.append(_make(
                "BSL002",
                DiagnosticSeverity.ERROR,
                f"Duplicate invariant name {invariant.name!r}; first defined at "
                f"{seen[invariant.name].line}:{seen[invariant.name].col}",
                invariant.span,
                suggestion=f"Rename one of the '{invariant.name}' invariants",
                rule="duplicate_invariants",
            ))
        else:
            seen[invariant.name] = invariant.span
    return diagnostics


# ---------------------------------------------------------------------------
# BSL003 — undefined behavior references in applies_to
# ---------------------------------------------------------------------------

def rule_undefined_applies_to(spec: AgentSpec) -> list[Diagnostic]:
    """BSL003: Behavior names in applies_to must be defined."""
    diagnostics: list[Diagnostic] = []
    defined_names = {b.name for b in spec.behaviors}
    for invariant in spec.invariants:
        if invariant.applies_to is AppliesTo.NAMED:
            for name in invariant.named_behaviors:
                if name not in defined_names:
                    diagnostics.append(_make(
                        "BSL003",
                        DiagnosticSeverity.ERROR,
                        f"Invariant {invariant.name!r} references undefined behavior {name!r}",
                        invariant.span,
                        suggestion=f"Define a behavior named '{name}' or remove it from applies_to",
                        rule="undefined_applies_to",
                    ))
    return diagnostics


# ---------------------------------------------------------------------------
# BSL004 — percentage out of range
# ---------------------------------------------------------------------------

def rule_percentage_range(spec: AgentSpec) -> list[Diagnostic]:
    """BSL004: Should-constraint percentages must be in [0, 100]."""
    diagnostics: list[Diagnostic] = []
    for behavior in spec.behaviors:
        for should in behavior.should_constraints:
            if should.percentage is not None:
                if not (0.0 <= should.percentage <= 100.0):
                    diagnostics.append(_make(
                        "BSL004",
                        DiagnosticSeverity.ERROR,
                        f"Behavior {behavior.name!r}: should-constraint percentage "
                        f"{should.percentage} is outside the valid range [0, 100]",
                        should.span,
                        suggestion="Use a percentage value between 0 and 100",
                        rule="percentage_range",
                    ))
    return diagnostics


# ---------------------------------------------------------------------------
# BSL005 — empty behaviors
# ---------------------------------------------------------------------------

def rule_empty_behaviors(spec: AgentSpec) -> list[Diagnostic]:
    """BSL005: A behavior with no constraints is likely a mistake."""
    diagnostics: list[Diagnostic] = []
    for behavior in spec.behaviors:
        total = (
            len(behavior.must_constraints)
            + len(behavior.must_not_constraints)
            + len(behavior.should_constraints)
            + len(behavior.may_constraints)
        )
        if total == 0:
            diagnostics.append(_make(
                "BSL005",
                DiagnosticSeverity.WARNING,
                f"Behavior {behavior.name!r} has no constraints (must, must_not, should, or may)",
                behavior.span,
                suggestion="Add at least one constraint to the behavior",
                rule="empty_behaviors",
            ))
    return diagnostics


# ---------------------------------------------------------------------------
# BSL006 — missing model metadata
# ---------------------------------------------------------------------------

def rule_missing_model(spec: AgentSpec) -> list[Diagnostic]:
    """BSL006: Agents should declare the model they run on."""
    diagnostics: list[Diagnostic] = []
    if spec.model is None:
        diagnostics.append(_make(
            "BSL006",
            DiagnosticSeverity.WARNING,
            f"Agent {spec.name!r} does not declare a 'model' field",
            spec.span,
            suggestion='Add: model: "gpt-4o"',
            rule="missing_model",
        ))
    return diagnostics


# ---------------------------------------------------------------------------
# BSL007 — missing version metadata
# ---------------------------------------------------------------------------

def rule_missing_version(spec: AgentSpec) -> list[Diagnostic]:
    """BSL007: Agents should declare a version for traceability."""
    diagnostics: list[Diagnostic] = []
    if spec.version is None:
        diagnostics.append(_make(
            "BSL007",
            DiagnosticSeverity.WARNING,
            f"Agent {spec.name!r} does not declare a 'version' field",
            spec.span,
            suggestion='Add: version: "1.0.0"',
            rule="missing_version",
        ))
    return diagnostics


# ---------------------------------------------------------------------------
# BSL008 — conflicting must / must_not constraints
# ---------------------------------------------------------------------------

def rule_conflicting_constraints(spec: AgentSpec) -> list[Diagnostic]:
    """BSL008: The same expression should not appear in both must and must_not."""
    diagnostics: list[Diagnostic] = []
    for behavior in spec.behaviors:
        must_strs = {_expr_to_str(c.expression) for c in behavior.must_constraints}
        for prohibition in behavior.must_not_constraints:
            key = _expr_to_str(prohibition.expression)
            if key in must_strs:
                diagnostics.append(_make(
                    "BSL008",
                    DiagnosticSeverity.ERROR,
                    f"Behavior {behavior.name!r}: expression {key!r} appears in "
                    "both 'must' and 'must_not' — this is a contradiction",
                    prohibition.span,
                    suggestion="Remove the expression from either must or must_not",
                    rule="conflicting_constraints",
                ))
    return diagnostics


# ---------------------------------------------------------------------------
# BSL009 — degradation references undefined behavior
# ---------------------------------------------------------------------------

def rule_undefined_degradation_target(spec: AgentSpec) -> list[Diagnostic]:
    """BSL009: A degrades_to target should be a defined behavior name."""
    diagnostics: list[Diagnostic] = []
    defined_names = {b.name for b in spec.behaviors}
    for degradation in spec.degradations:
        if degradation.fallback not in defined_names:
            diagnostics.append(_make(
                "BSL009",
                DiagnosticSeverity.WARNING,
                f"degrades_to references {degradation.fallback!r} which is not a defined behavior",
                degradation.span,
                suggestion=(
                    f"Define a behavior named '{degradation.fallback}' or correct the spelling"
                ),
                rule="undefined_degradation_target",
            ))
    return diagnostics


# ---------------------------------------------------------------------------
# BSL010 — threshold value sanity
# ---------------------------------------------------------------------------

def rule_threshold_sanity(spec: AgentSpec) -> list[Diagnostic]:
    """BSL010: Threshold values must be non-negative; confidence must be in [0, 100]."""
    diagnostics: list[Diagnostic] = []
    for behavior in spec.behaviors:
        if behavior.confidence is not None:
            pct = behavior.confidence.value
            if behavior.confidence.is_percentage and not (0.0 <= pct <= 100.0):
                diagnostics.append(_make(
                    "BSL010",
                    DiagnosticSeverity.ERROR,
                    f"Behavior {behavior.name!r}: confidence percentage {pct} is out of range [0, 100]",
                    behavior.confidence.span,
                    suggestion="Use a value between 0 and 100",
                    rule="threshold_sanity",
                ))
        if behavior.latency is not None and behavior.latency.value < 0:
            diagnostics.append(_make(
                "BSL010",
                DiagnosticSeverity.ERROR,
                f"Behavior {behavior.name!r}: latency threshold cannot be negative",
                behavior.latency.span,
                suggestion="Use a non-negative latency value",
                rule="threshold_sanity",
            ))
        if behavior.cost is not None and behavior.cost.value < 0:
            diagnostics.append(_make(
                "BSL010",
                DiagnosticSeverity.ERROR,
                f"Behavior {behavior.name!r}: cost threshold cannot be negative",
                behavior.cost.span,
                suggestion="Use a non-negative cost value",
                rule="threshold_sanity",
            ))
    return diagnostics


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------

DEFAULT_RULES: list[Rule] = [
    rule_duplicate_behaviors,
    rule_duplicate_invariants,
    rule_undefined_applies_to,
    rule_percentage_range,
    rule_empty_behaviors,
    rule_missing_model,
    rule_missing_version,
    rule_conflicting_constraints,
    rule_undefined_degradation_target,
    rule_threshold_sanity,
]
