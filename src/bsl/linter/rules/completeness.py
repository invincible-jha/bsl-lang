"""Completeness lint rules for BSL.

These rules flag agent specifications that are missing fields or
sections that are considered best practice for production-quality
behavior specifications.

Rule codes:
    LINT-C001  No behaviors defined
    LINT-C002  No invariants defined
    LINT-C003  Behavior missing confidence threshold
    LINT-C004  Behavior missing latency threshold
    LINT-C005  Agent has no owner
    LINT-C006  Invariant has no constraints or prohibitions
    LINT-C007  Behavior has no when-clause (unconditional behaviors may be overly broad)
    LINT-C008  No audit level set on any behavior
"""
from __future__ import annotations

from bsl.ast.nodes import AgentSpec, AuditLevel
from bsl.validator.diagnostics import Diagnostic, DiagnosticSeverity


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
        rule="completeness",
    )


def rule_has_behaviors(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-C001: An agent with no behaviors is likely incomplete."""
    if not spec.behaviors:
        return [_diag(
            "LINT-C001",
            DiagnosticSeverity.WARNING,
            f"Agent {spec.name!r} defines no behaviors",
            spec.span,
            suggestion="Add at least one behavior block",
        )]
    return []


def rule_has_invariants(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-C002: Agents should define invariants for cross-cutting guarantees."""
    if not spec.invariants:
        return [_diag(
            "LINT-C002",
            DiagnosticSeverity.HINT,
            f"Agent {spec.name!r} defines no invariants",
            spec.span,
            suggestion="Add invariant blocks for cross-cutting behavioral guarantees",
        )]
    return []


def rule_behavior_has_confidence(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-C003: Production behaviors should declare a confidence threshold."""
    diagnostics: list[Diagnostic] = []
    for behavior in spec.behaviors:
        if behavior.confidence is None:
            diagnostics.append(_diag(
                "LINT-C003",
                DiagnosticSeverity.HINT,
                f"Behavior {behavior.name!r} has no confidence threshold",
                behavior.span,
                suggestion='Add: confidence: >= 0.9',
            ))
    return diagnostics


def rule_behavior_has_latency(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-C004: Production behaviors should declare a latency threshold."""
    diagnostics: list[Diagnostic] = []
    for behavior in spec.behaviors:
        if behavior.latency is None:
            diagnostics.append(_diag(
                "LINT-C004",
                DiagnosticSeverity.HINT,
                f"Behavior {behavior.name!r} has no latency threshold",
                behavior.span,
                suggestion="Add: latency: < 2000  // milliseconds",
            ))
    return diagnostics


def rule_agent_has_owner(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-C005: Agents should declare an owner for accountability."""
    if spec.owner is None:
        return [_diag(
            "LINT-C005",
            DiagnosticSeverity.WARNING,
            f"Agent {spec.name!r} has no 'owner' field",
            spec.span,
            suggestion='Add: owner: "team-name@example.com"',
        )]
    return []


def rule_invariant_has_content(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-C006: Invariants with no constraints are empty shells."""
    diagnostics: list[Diagnostic] = []
    for invariant in spec.invariants:
        total = len(invariant.constraints) + len(invariant.prohibitions)
        if total == 0:
            diagnostics.append(_diag(
                "LINT-C006",
                DiagnosticSeverity.WARNING,
                f"Invariant {invariant.name!r} has no must or must_not clauses",
                invariant.span,
                suggestion="Add must or must_not constraints to the invariant",
            ))
    return diagnostics


def rule_audit_coverage(spec: AgentSpec) -> list[Diagnostic]:
    """LINT-C008: At least one behavior should have audit logging enabled."""
    diagnostics: list[Diagnostic] = []
    if spec.behaviors:
        has_audit = any(b.audit != AuditLevel.NONE for b in spec.behaviors)
        if not has_audit:
            diagnostics.append(_diag(
                "LINT-C008",
                DiagnosticSeverity.HINT,
                f"Agent {spec.name!r}: no behaviors have audit logging enabled",
                spec.span,
                suggestion="Add 'audit: basic' or 'audit: full_trace' to key behaviors",
            ))
    return diagnostics


COMPLETENESS_RULES = [
    rule_has_behaviors,
    rule_has_invariants,
    rule_behavior_has_confidence,
    rule_behavior_has_latency,
    rule_agent_has_owner,
    rule_invariant_has_content,
    rule_audit_coverage,
]
