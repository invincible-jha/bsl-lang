"""Unit tests for bsl.diff.diff — BslDiff engine and all BslChange types."""
from __future__ import annotations

import pytest

from bsl.ast.nodes import (
    AgentSpec,
    AppliesTo,
    AuditLevel,
    Behavior,
    BinOp,
    BinaryOpExpr,
    BoolLit,
    Composition,
    Constraint,
    ContainsExpr,
    Delegates,
    DotAccess,
    EscalationClause,
    FunctionCall,
    Identifier,
    InListExpr,
    Invariant,
    NumberLit,
    Receives,
    Severity,
    ShouldConstraint,
    Span,
    StringLit,
    ThresholdClause,
    UnaryOpExpr,
    UnaryOpKind,
    Degradation,
    AfterExpr,
    BeforeExpr,
)
from bsl.diff.diff import (
    AuditLevelChanged,
    BehaviorAdded,
    BehaviorRemoved,
    BslDiff,
    ChangeKind,
    CompositionAdded,
    CompositionRemoved,
    ConstraintAdded,
    ConstraintModified,
    ConstraintRemoved,
    DegradationChanged,
    EscalationChanged,
    InvariantAdded,
    InvariantRemoved,
    MetadataChanged,
    SeverityChanged,
    ThresholdChanged,
    WhenClauseChanged,
    diff,
)

_S = Span.unknown()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ident(name: str) -> Identifier:
    return Identifier(name=name, span=_S)


def _constraint(name: str) -> Constraint:
    return Constraint(expression=_ident(name), span=_S)


def _should(name: str, pct: float | None = None) -> ShouldConstraint:
    return ShouldConstraint(expression=_ident(name), percentage=pct, span=_S)


def _threshold(op: str, value: float, pct: bool = False) -> ThresholdClause:
    return ThresholdClause(operator=op, value=value, is_percentage=pct, span=_S)


def _escalation(cond: str) -> EscalationClause:
    return EscalationClause(condition=_ident(cond), span=_S)


def _behavior(
    name: str,
    *,
    when_clause: object | None = None,
    must: tuple[Constraint, ...] = (),
    must_not: tuple[Constraint, ...] = (),
    should: tuple[ShouldConstraint, ...] = (),
    may: tuple[Constraint, ...] = (),
    confidence: ThresholdClause | None = None,
    latency: ThresholdClause | None = None,
    cost: ThresholdClause | None = None,
    escalation: EscalationClause | None = None,
    audit: AuditLevel = AuditLevel.NONE,
) -> Behavior:
    return Behavior(
        name=name,
        when_clause=when_clause,  # type: ignore[arg-type]
        must_constraints=must,
        must_not_constraints=must_not,
        should_constraints=should,
        may_constraints=may,
        confidence=confidence,
        latency=latency,
        cost=cost,
        escalation=escalation,
        audit=audit,
        span=_S,
    )


def _invariant(
    name: str,
    *,
    severity: Severity = Severity.HIGH,
    applies_to: AppliesTo = AppliesTo.ALL_BEHAVIORS,
    named_behaviors: tuple[str, ...] = (),
    constraints: tuple[Constraint, ...] = (),
    prohibitions: tuple[Constraint, ...] = (),
) -> Invariant:
    return Invariant(
        name=name,
        constraints=constraints,
        prohibitions=prohibitions,
        applies_to=applies_to,
        named_behaviors=named_behaviors,
        severity=severity,
        span=_S,
    )


def _spec(
    name: str = "TestAgent",
    *,
    version: str | None = "1.0.0",
    model: str | None = "gpt-4o",
    owner: str | None = "team@example.com",
    behaviors: tuple[Behavior, ...] = (),
    invariants: tuple[Invariant, ...] = (),
    degradations: tuple[Degradation, ...] = (),
    compositions: tuple[Composition, ...] = (),
) -> AgentSpec:
    return AgentSpec(
        name=name,
        version=version,
        model=model,
        owner=owner,
        behaviors=behaviors,
        invariants=invariants,
        degradations=degradations,
        compositions=compositions,
        span=_S,
    )


# ===========================================================================
# Change dataclass __str__ methods
# ===========================================================================


class TestChangeStrRepresentations:
    def test_behavior_added_str(self) -> None:
        c = BehaviorAdded(behavior_name="greet")
        assert "greet" in str(c)
        assert "+" in str(c)

    def test_behavior_removed_str(self) -> None:
        c = BehaviorRemoved(behavior_name="greet")
        assert "greet" in str(c)
        assert "-" in str(c)

    def test_constraint_added_str(self) -> None:
        c = ConstraintAdded(behavior_name="b", constraint_type="must", expression="safe")
        text = str(c)
        assert "b" in text
        assert "must" in text
        assert "safe" in text

    def test_constraint_removed_str(self) -> None:
        c = ConstraintRemoved(behavior_name="b", constraint_type="must_not", expression="harmful")
        assert "harmful" in str(c)

    def test_constraint_modified_str(self) -> None:
        c = ConstraintModified(
            behavior_name="b",
            constraint_type="must",
            old_expression="old_expr",
            new_expression="new_expr",
        )
        text = str(c)
        assert "old_expr" in text
        assert "new_expr" in text

    def test_invariant_added_str(self) -> None:
        c = InvariantAdded(invariant_name="safety")
        assert "safety" in str(c)

    def test_invariant_removed_str(self) -> None:
        c = InvariantRemoved(invariant_name="safety")
        assert "safety" in str(c)

    def test_threshold_changed_str(self) -> None:
        c = ThresholdChanged(
            behavior_name="b",
            field_name="confidence",
            old_value=">=0.9",
            new_value=">=0.95",
        )
        text = str(c)
        assert "confidence" in text
        assert ">=0.9" in text

    def test_severity_changed_str(self) -> None:
        c = SeverityChanged(
            invariant_name="safety",
            old_severity="HIGH",
            new_severity="CRITICAL",
        )
        text = str(c)
        assert "safety" in text
        assert "HIGH" in text
        assert "CRITICAL" in text

    def test_degradation_changed_str(self) -> None:
        c = DegradationChanged(description="Removed: degrades_to fallback")
        assert "fallback" in str(c)

    def test_composition_added_str(self) -> None:
        c = CompositionAdded(description="receives from InputAgent")
        assert "InputAgent" in str(c)

    def test_composition_removed_str(self) -> None:
        c = CompositionRemoved(description="delegates_to ChildAgent")
        assert "ChildAgent" in str(c)

    def test_metadata_changed_str(self) -> None:
        c = MetadataChanged(field_name="model", old_value="gpt-3", new_value="gpt-4o")
        text = str(c)
        assert "model" in text
        assert "gpt-3" in text

    def test_when_clause_changed_str(self) -> None:
        c = WhenClauseChanged(behavior_name="b", old_when="old", new_when="new")
        assert "b" in str(c)
        assert "old" in str(c)

    def test_audit_level_changed_str(self) -> None:
        c = AuditLevelChanged(behavior_name="b", old_level="NONE", new_level="BASIC")
        assert "NONE" in str(c)
        assert "BASIC" in str(c)

    def test_escalation_changed_str(self) -> None:
        c = EscalationChanged(behavior_name="b", description="'None' → 'angry'")
        assert "angry" in str(c)


# ===========================================================================
# ChangeKind enum
# ===========================================================================


class TestChangeKind:
    def test_all_kinds_exist(self) -> None:
        kinds = [
            ChangeKind.BEHAVIOR_ADDED,
            ChangeKind.BEHAVIOR_REMOVED,
            ChangeKind.CONSTRAINT_ADDED,
            ChangeKind.CONSTRAINT_REMOVED,
            ChangeKind.CONSTRAINT_MODIFIED,
            ChangeKind.INVARIANT_ADDED,
            ChangeKind.INVARIANT_REMOVED,
            ChangeKind.THRESHOLD_CHANGED,
            ChangeKind.SEVERITY_CHANGED,
            ChangeKind.DEGRADATION_CHANGED,
            ChangeKind.COMPOSITION_ADDED,
            ChangeKind.COMPOSITION_REMOVED,
            ChangeKind.METADATA_CHANGED,
            ChangeKind.WHEN_CLAUSE_CHANGED,
            ChangeKind.AUDIT_LEVEL_CHANGED,
            ChangeKind.ESCALATION_CHANGED,
        ]
        assert len(kinds) == 16


# ===========================================================================
# BslDiff.diff — identical specs
# ===========================================================================


class TestBslDiffIdentical:
    def setup_method(self) -> None:
        self.differ = BslDiff()

    def test_identical_empty_specs_returns_no_changes(self) -> None:
        spec = _spec()
        assert self.differ.diff(spec, spec) == []

    def test_identical_specs_with_behavior_returns_no_changes(self) -> None:
        beh = _behavior("respond", must=(_constraint("safe"),))
        spec = _spec(behaviors=(beh,))
        assert self.differ.diff(spec, spec) == []

    def test_identical_metadata_returns_no_changes(self) -> None:
        spec = _spec(version="1.0.0", model="gpt-4o", owner="team")
        assert self.differ.diff(spec, spec) == []


# ===========================================================================
# Metadata changes
# ===========================================================================


class TestBslDiffMetadata:
    def setup_method(self) -> None:
        self.differ = BslDiff()

    def test_version_change_detected(self) -> None:
        old = _spec(version="1.0.0")
        new = _spec(version="2.0.0")
        changes = self.differ.diff(old, new)
        meta = [c for c in changes if isinstance(c, MetadataChanged)]
        assert len(meta) == 1
        assert meta[0].field_name == "version"
        assert meta[0].old_value == "1.0.0"
        assert meta[0].new_value == "2.0.0"

    def test_model_change_detected(self) -> None:
        old = _spec(model="gpt-3")
        new = _spec(model="gpt-4o")
        changes = self.differ.diff(old, new)
        meta = [c for c in changes if isinstance(c, MetadataChanged)]
        assert any(c.field_name == "model" for c in meta)

    def test_owner_change_detected(self) -> None:
        old = _spec(owner="alice@example.com")
        new = _spec(owner="bob@example.com")
        changes = self.differ.diff(old, new)
        meta = [c for c in changes if isinstance(c, MetadataChanged)]
        assert any(c.field_name == "owner" for c in meta)

    def test_version_none_to_set_detected(self) -> None:
        old = _spec(version=None)
        new = _spec(version="1.0.0")
        changes = self.differ.diff(old, new)
        meta = [c for c in changes if isinstance(c, MetadataChanged) and c.field_name == "version"]
        assert len(meta) == 1
        assert meta[0].old_value is None
        assert meta[0].new_value == "1.0.0"

    def test_no_metadata_change_returns_no_meta_changes(self) -> None:
        spec = _spec(version="1.0", model="m", owner="o")
        changes = self.differ.diff(spec, spec)
        assert not any(isinstance(c, MetadataChanged) for c in changes)


# ===========================================================================
# Behavior changes
# ===========================================================================


class TestBslDiffBehaviors:
    def setup_method(self) -> None:
        self.differ = BslDiff()

    def test_behavior_added(self) -> None:
        old = _spec()
        new = _spec(behaviors=(_behavior("greet"),))
        changes = self.differ.diff(old, new)
        added = [c for c in changes if isinstance(c, BehaviorAdded)]
        assert len(added) == 1
        assert added[0].behavior_name == "greet"

    def test_behavior_removed(self) -> None:
        old = _spec(behaviors=(_behavior("greet"),))
        new = _spec()
        changes = self.differ.diff(old, new)
        removed = [c for c in changes if isinstance(c, BehaviorRemoved)]
        assert len(removed) == 1
        assert removed[0].behavior_name == "greet"

    def test_multiple_behaviors_added(self) -> None:
        old = _spec()
        new = _spec(behaviors=(_behavior("a"), _behavior("b")))
        changes = self.differ.diff(old, new)
        added = {c.behavior_name for c in changes if isinstance(c, BehaviorAdded)}
        assert added == {"a", "b"}

    def test_must_constraint_added(self) -> None:
        old = _spec(behaviors=(_behavior("respond"),))
        new = _spec(behaviors=(_behavior("respond", must=(_constraint("safe"),)),))
        changes = self.differ.diff(old, new)
        added = [c for c in changes if isinstance(c, ConstraintAdded)]
        assert len(added) == 1
        assert added[0].constraint_type == "must"
        assert added[0].expression == "safe"

    def test_must_constraint_removed(self) -> None:
        old = _spec(behaviors=(_behavior("respond", must=(_constraint("safe"),)),))
        new = _spec(behaviors=(_behavior("respond"),))
        changes = self.differ.diff(old, new)
        removed = [c for c in changes if isinstance(c, ConstraintRemoved)]
        assert len(removed) == 1
        assert removed[0].expression == "safe"

    def test_must_not_constraint_added(self) -> None:
        old = _spec(behaviors=(_behavior("respond"),))
        new = _spec(behaviors=(_behavior("respond", must_not=(_constraint("harmful"),)),))
        changes = self.differ.diff(old, new)
        added = [c for c in changes if isinstance(c, ConstraintAdded)]
        assert any(c.constraint_type == "must_not" for c in added)

    def test_should_constraint_added(self) -> None:
        old = _spec(behaviors=(_behavior("respond"),))
        new = _spec(behaviors=(_behavior("respond", should=(_should("polite"),)),))
        changes = self.differ.diff(old, new)
        added = [c for c in changes if isinstance(c, ConstraintAdded)]
        assert any(c.constraint_type == "should" for c in added)

    def test_may_constraint_added(self) -> None:
        old = _spec(behaviors=(_behavior("respond"),))
        new = _spec(behaviors=(_behavior("respond", may=(_constraint("suggest"),)),))
        changes = self.differ.diff(old, new)
        added = [c for c in changes if isinstance(c, ConstraintAdded)]
        assert any(c.constraint_type == "may" for c in added)

    def test_confidence_threshold_changed(self) -> None:
        old_conf = _threshold(">=", 0.9)
        new_conf = _threshold(">=", 0.95)
        old = _spec(behaviors=(_behavior("b", confidence=old_conf),))
        new = _spec(behaviors=(_behavior("b", confidence=new_conf),))
        changes = self.differ.diff(old, new)
        thresh = [c for c in changes if isinstance(c, ThresholdChanged)]
        assert len(thresh) == 1
        assert thresh[0].field_name == "confidence"

    def test_latency_threshold_changed(self) -> None:
        old = _spec(behaviors=(_behavior("b", latency=_threshold("<", 500.0)),))
        new = _spec(behaviors=(_behavior("b", latency=_threshold("<", 250.0)),))
        changes = self.differ.diff(old, new)
        thresh = [c for c in changes if isinstance(c, ThresholdChanged)]
        assert any(c.field_name == "latency" for c in thresh)

    def test_cost_threshold_changed(self) -> None:
        old = _spec(behaviors=(_behavior("b", cost=_threshold("<", 0.05)),))
        new = _spec(behaviors=(_behavior("b", cost=_threshold("<", 0.02)),))
        changes = self.differ.diff(old, new)
        thresh = [c for c in changes if isinstance(c, ThresholdChanged)]
        assert any(c.field_name == "cost" for c in thresh)

    def test_threshold_added_from_none(self) -> None:
        old = _spec(behaviors=(_behavior("b"),))
        new = _spec(behaviors=(_behavior("b", confidence=_threshold(">=", 0.9)),))
        changes = self.differ.diff(old, new)
        thresh = [c for c in changes if isinstance(c, ThresholdChanged)]
        assert any(c.field_name == "confidence" for c in thresh)

    def test_threshold_removed_to_none(self) -> None:
        old = _spec(behaviors=(_behavior("b", confidence=_threshold(">=", 0.9)),))
        new = _spec(behaviors=(_behavior("b"),))
        changes = self.differ.diff(old, new)
        thresh = [c for c in changes if isinstance(c, ThresholdChanged)]
        assert any(c.field_name == "confidence" for c in thresh)

    def test_audit_level_changed(self) -> None:
        old = _spec(behaviors=(_behavior("b", audit=AuditLevel.NONE),))
        new = _spec(behaviors=(_behavior("b", audit=AuditLevel.BASIC),))
        changes = self.differ.diff(old, new)
        audit_changes = [c for c in changes if isinstance(c, AuditLevelChanged)]
        assert len(audit_changes) == 1
        assert audit_changes[0].old_level == "NONE"
        assert audit_changes[0].new_level == "BASIC"

    def test_when_clause_changed(self) -> None:
        old = _spec(behaviors=(_behavior("b", when_clause=_ident("cond_a")),))
        new = _spec(behaviors=(_behavior("b", when_clause=_ident("cond_b")),))
        changes = self.differ.diff(old, new)
        when = [c for c in changes if isinstance(c, WhenClauseChanged)]
        assert len(when) == 1
        assert when[0].old_when == "cond_a"
        assert when[0].new_when == "cond_b"

    def test_when_clause_added(self) -> None:
        old = _spec(behaviors=(_behavior("b"),))
        new = _spec(behaviors=(_behavior("b", when_clause=_ident("online")),))
        changes = self.differ.diff(old, new)
        when = [c for c in changes if isinstance(c, WhenClauseChanged)]
        assert len(when) == 1
        assert when[0].old_when is None
        assert when[0].new_when == "online"

    def test_escalation_changed(self) -> None:
        old = _spec(behaviors=(_behavior("b", escalation=_escalation("angry")),))
        new = _spec(behaviors=(_behavior("b", escalation=_escalation("confused")),))
        changes = self.differ.diff(old, new)
        esc = [c for c in changes if isinstance(c, EscalationChanged)]
        assert len(esc) == 1

    def test_escalation_added(self) -> None:
        old = _spec(behaviors=(_behavior("b"),))
        new = _spec(behaviors=(_behavior("b", escalation=_escalation("angry")),))
        changes = self.differ.diff(old, new)
        esc = [c for c in changes if isinstance(c, EscalationChanged)]
        assert len(esc) == 1

    def test_no_changes_in_unchanged_behavior(self) -> None:
        beh = _behavior("respond", must=(_constraint("safe"),))
        spec = _spec(behaviors=(beh,))
        changes = self.differ.diff(spec, spec)
        assert changes == []


# ===========================================================================
# Invariant changes
# ===========================================================================


class TestBslDiffInvariants:
    def setup_method(self) -> None:
        self.differ = BslDiff()

    def test_invariant_added(self) -> None:
        old = _spec()
        new = _spec(invariants=(_invariant("safety"),))
        changes = self.differ.diff(old, new)
        added = [c for c in changes if isinstance(c, InvariantAdded)]
        assert len(added) == 1
        assert added[0].invariant_name == "safety"

    def test_invariant_removed(self) -> None:
        old = _spec(invariants=(_invariant("safety"),))
        new = _spec()
        changes = self.differ.diff(old, new)
        removed = [c for c in changes if isinstance(c, InvariantRemoved)]
        assert len(removed) == 1
        assert removed[0].invariant_name == "safety"

    def test_invariant_severity_changed(self) -> None:
        old = _spec(invariants=(_invariant("safety", severity=Severity.HIGH),))
        new = _spec(invariants=(_invariant("safety", severity=Severity.CRITICAL),))
        changes = self.differ.diff(old, new)
        sev = [c for c in changes if isinstance(c, SeverityChanged)]
        assert len(sev) == 1
        assert sev[0].old_severity == "HIGH"
        assert sev[0].new_severity == "CRITICAL"

    def test_invariant_severity_unchanged_no_change(self) -> None:
        spec = _spec(invariants=(_invariant("safety", severity=Severity.HIGH),))
        changes = self.differ.diff(spec, spec)
        assert not any(isinstance(c, SeverityChanged) for c in changes)


# ===========================================================================
# Degradation changes
# ===========================================================================


class TestBslDiffDegradations:
    def setup_method(self) -> None:
        self.differ = BslDiff()

    def test_degradation_added(self) -> None:
        deg = Degradation(fallback="fallback", condition=_ident("overloaded"), span=_S)
        old = _spec()
        new = _spec(degradations=(deg,))
        changes = self.differ.diff(old, new)
        deg_changes = [c for c in changes if isinstance(c, DegradationChanged)]
        assert len(deg_changes) == 1
        assert "fallback" in deg_changes[0].description

    def test_degradation_removed(self) -> None:
        deg = Degradation(fallback="fallback", condition=_ident("overloaded"), span=_S)
        old = _spec(degradations=(deg,))
        new = _spec()
        changes = self.differ.diff(old, new)
        deg_changes = [c for c in changes if isinstance(c, DegradationChanged)]
        assert len(deg_changes) == 1

    def test_degradation_condition_changed(self) -> None:
        old_deg = Degradation(fallback="fb", condition=_ident("cond_a"), span=_S)
        new_deg = Degradation(fallback="fb", condition=_ident("cond_b"), span=_S)
        old = _spec(degradations=(old_deg,))
        new = _spec(degradations=(new_deg,))
        changes = self.differ.diff(old, new)
        deg_changes = [c for c in changes if isinstance(c, DegradationChanged)]
        assert len(deg_changes) == 1
        assert "cond_a" in deg_changes[0].description
        assert "cond_b" in deg_changes[0].description


# ===========================================================================
# Composition changes
# ===========================================================================


class TestBslDiffCompositions:
    def setup_method(self) -> None:
        self.differ = BslDiff()

    def test_receives_composition_added(self) -> None:
        rec = Receives(source_agent="InputAgent", span=_S)
        old = _spec()
        new = _spec(compositions=(rec,))
        changes = self.differ.diff(old, new)
        added = [c for c in changes if isinstance(c, CompositionAdded)]
        assert len(added) == 1
        assert "InputAgent" in added[0].description

    def test_delegates_composition_removed(self) -> None:
        dlg = Delegates(target_agent="ChildAgent", span=_S)
        old = _spec(compositions=(dlg,))
        new = _spec()
        changes = self.differ.diff(old, new)
        removed = [c for c in changes if isinstance(c, CompositionRemoved)]
        assert len(removed) == 1
        assert "ChildAgent" in removed[0].description

    def test_unchanged_composition_returns_no_change(self) -> None:
        rec = Receives(source_agent="InputAgent", span=_S)
        spec = _spec(compositions=(rec,))
        assert self.differ.diff(spec, spec) == []


# ===========================================================================
# Convenience diff() function
# ===========================================================================


class TestDiffConvenienceFunction:
    def test_returns_list(self) -> None:
        spec = _spec()
        assert isinstance(diff(spec, spec), list)

    def test_detects_behavior_added(self) -> None:
        old = _spec()
        new = _spec(behaviors=(_behavior("new_beh"),))
        changes = diff(old, new)
        assert any(isinstance(c, BehaviorAdded) for c in changes)

    def test_empty_diff_for_identical_specs(self) -> None:
        spec = _spec(behaviors=(_behavior("b", must=(_constraint("safe"),)),))
        assert diff(spec, spec) == []


# ===========================================================================
# Expression helper (_expr_str coverage via constraint diffs)
# ===========================================================================


class TestExprStrCoverage:
    """Drive _expr_str through constraint diffs to cover all expression types."""

    def setup_method(self) -> None:
        self.differ = BslDiff()

    def _constraint_change(self, old_expr: object, new_expr: object) -> list:
        old = _spec(behaviors=(_behavior("b", must=(Constraint(expression=old_expr, span=_S),)),))  # type: ignore[arg-type]
        new = _spec(behaviors=(_behavior("b", must=(Constraint(expression=new_expr, span=_S),)),))  # type: ignore[arg-type]
        return self.differ.diff(old, new)

    def test_dot_access_expr(self) -> None:
        dot = DotAccess(parts=("response", "status"), span=_S)
        changes = self._constraint_change(Identifier(name="x", span=_S), dot)
        assert any(isinstance(c, ConstraintAdded) and "response.status" in c.expression for c in changes)

    def test_string_lit_expr(self) -> None:
        changes = self._constraint_change(Identifier(name="x", span=_S), StringLit(value="hello", span=_S))
        assert any(isinstance(c, ConstraintAdded) and '"hello"' in c.expression for c in changes)

    def test_number_lit_expr(self) -> None:
        changes = self._constraint_change(Identifier(name="x", span=_S), NumberLit(value=42.0, span=_S))
        assert any(isinstance(c, ConstraintAdded) and "42" in c.expression for c in changes)

    def test_bool_lit_expr(self) -> None:
        changes = self._constraint_change(Identifier(name="x", span=_S), BoolLit(value=True, span=_S))
        assert any(isinstance(c, ConstraintAdded) and "true" in c.expression for c in changes)

    def test_binary_op_expr(self) -> None:
        binary = BinaryOpExpr(
            op=BinOp.EQ,
            left=Identifier(name="a", span=_S),
            right=Identifier(name="b", span=_S),
            span=_S,
        )
        changes = self._constraint_change(Identifier(name="x", span=_S), binary)
        assert any(isinstance(c, ConstraintAdded) and "eq" in c.expression.lower() for c in changes)

    def test_unary_op_expr(self) -> None:
        unary = UnaryOpExpr(
            op=UnaryOpKind.NOT,
            operand=Identifier(name="flagged", span=_S),
            span=_S,
        )
        changes = self._constraint_change(Identifier(name="x", span=_S), unary)
        assert any(isinstance(c, ConstraintAdded) and "not flagged" in c.expression for c in changes)

    def test_contains_expr(self) -> None:
        contains = ContainsExpr(
            subject=Identifier(name="response", span=_S),
            value=StringLit(value="error", span=_S),
            span=_S,
        )
        changes = self._constraint_change(Identifier(name="x", span=_S), contains)
        assert any(isinstance(c, ConstraintAdded) and "contains" in c.expression for c in changes)

    def test_in_list_expr(self) -> None:
        in_list = InListExpr(
            subject=Identifier(name="status", span=_S),
            items=(NumberLit(value=200.0, span=_S), NumberLit(value=201.0, span=_S)),
            span=_S,
        )
        changes = self._constraint_change(Identifier(name="x", span=_S), in_list)
        assert any(isinstance(c, ConstraintAdded) and "in" in c.expression for c in changes)

    def test_before_expr(self) -> None:
        before = BeforeExpr(
            left=Identifier(name="a", span=_S),
            right=Identifier(name="b", span=_S),
            span=_S,
        )
        changes = self._constraint_change(Identifier(name="x", span=_S), before)
        assert any(isinstance(c, ConstraintAdded) and "before" in c.expression for c in changes)

    def test_after_expr(self) -> None:
        after = AfterExpr(
            left=Identifier(name="a", span=_S),
            right=Identifier(name="b", span=_S),
            span=_S,
        )
        changes = self._constraint_change(Identifier(name="x", span=_S), after)
        assert any(isinstance(c, ConstraintAdded) and "after" in c.expression for c in changes)

    def test_function_call_expr(self) -> None:
        call = FunctionCall(
            name="len",
            arguments=(Identifier(name="items", span=_S),),
            span=_S,
        )
        changes = self._constraint_change(Identifier(name="x", span=_S), call)
        assert any(isinstance(c, ConstraintAdded) and "len(items)" in c.expression for c in changes)

    def test_none_expr_returns_none_string(self) -> None:
        """_expr_str(None) should return '<none>'."""
        old = _spec(behaviors=(_behavior("b"),))
        new = _spec(behaviors=(_behavior("b", when_clause=_ident("cond")),))
        changes = self.differ.diff(old, new)
        when = [c for c in changes if isinstance(c, WhenClauseChanged)]
        assert len(when) == 1
        assert when[0].old_when is None
