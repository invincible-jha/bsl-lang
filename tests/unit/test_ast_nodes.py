"""Unit tests for bsl.ast.nodes — all AST dataclasses, enums, and helpers."""
from __future__ import annotations

import pytest

from bsl.ast.nodes import (
    AfterExpr,
    AgentSpec,
    AppliesTo,
    AuditLevel,
    Behavior,
    BeforeExpr,
    BinOp,
    BinaryOpExpr,
    BoolLit,
    Composition,
    Constraint,
    ContainsExpr,
    Degradation,
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
)


# ---------------------------------------------------------------------------
# Span
# ---------------------------------------------------------------------------


class TestSpan:
    def test_span_creation(self) -> None:
        span = Span(start=0, end=5, line=1, col=1)
        assert span.start == 0
        assert span.end == 5
        assert span.line == 1
        assert span.col == 1

    def test_span_is_frozen(self) -> None:
        span = Span(start=0, end=5, line=1, col=1)
        with pytest.raises((AttributeError, TypeError)):
            span.start = 99  # type: ignore[misc]

    def test_span_unknown_returns_zeros(self) -> None:
        span = Span.unknown()
        assert span.start == 0
        assert span.end == 0
        assert span.line == 0
        assert span.col == 0

    def test_span_repr(self) -> None:
        span = Span(start=0, end=10, line=3, col=7)
        r = repr(span)
        assert "3:7" in r

    def test_span_merge_covers_both(self) -> None:
        a = Span(start=0, end=5, line=1, col=1)
        b = Span(start=10, end=20, line=2, col=3)
        merged = a.merge(b)
        assert merged.start == 0
        assert merged.end == 20

    def test_span_merge_uses_min_line(self) -> None:
        a = Span(start=5, end=10, line=2, col=1)
        b = Span(start=0, end=3, line=1, col=5)
        merged = a.merge(b)
        assert merged.line == 1

    def test_span_merge_symmetric_start(self) -> None:
        a = Span(start=3, end=8, line=1, col=1)
        b = Span(start=0, end=5, line=1, col=1)
        merged = a.merge(b)
        assert merged.start == 0


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestAppliesTo:
    def test_all_behaviors_variant_exists(self) -> None:
        assert AppliesTo.ALL_BEHAVIORS is not None

    def test_named_variant_exists(self) -> None:
        assert AppliesTo.NAMED is not None


class TestSeverity:
    @pytest.mark.parametrize("level", ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
    def test_severity_level_exists(self, level: str) -> None:
        assert getattr(Severity, level) is not None


class TestAuditLevel:
    @pytest.mark.parametrize("level", ["NONE", "BASIC", "FULL_TRACE"])
    def test_audit_level_exists(self, level: str) -> None:
        assert getattr(AuditLevel, level) is not None


class TestBinOp:
    @pytest.mark.parametrize("op_name", [
        "AND", "OR", "EQ", "NEQ", "LT", "GT", "LTE", "GTE",
        "BEFORE", "AFTER", "CONTAINS", "IN",
    ])
    def test_binary_op_exists(self, op_name: str) -> None:
        assert getattr(BinOp, op_name) is not None


class TestUnaryOpKind:
    def test_not_variant_exists(self) -> None:
        assert UnaryOpKind.NOT is not None


# ---------------------------------------------------------------------------
# Literal nodes
# ---------------------------------------------------------------------------


_SPAN = Span.unknown()


class TestStringLit:
    def test_creation(self) -> None:
        lit = StringLit(value="hello", span=_SPAN)
        assert lit.value == "hello"

    def test_is_frozen(self) -> None:
        lit = StringLit(value="x", span=_SPAN)
        with pytest.raises((AttributeError, TypeError)):
            lit.value = "y"  # type: ignore[misc]


class TestNumberLit:
    def test_creation_integer(self) -> None:
        lit = NumberLit(value=42.0, span=_SPAN)
        assert lit.value == 42.0

    def test_creation_float(self) -> None:
        lit = NumberLit(value=3.14, span=_SPAN)
        assert lit.value == pytest.approx(3.14)


class TestBoolLit:
    def test_true_value(self) -> None:
        lit = BoolLit(value=True, span=_SPAN)
        assert lit.value is True

    def test_false_value(self) -> None:
        lit = BoolLit(value=False, span=_SPAN)
        assert lit.value is False


# ---------------------------------------------------------------------------
# Expression nodes
# ---------------------------------------------------------------------------


class TestIdentifier:
    def test_creation(self) -> None:
        ident = Identifier(name="response", span=_SPAN)
        assert ident.name == "response"


class TestDotAccess:
    def test_creation(self) -> None:
        dot = DotAccess(parts=("response", "status"), span=_SPAN)
        assert dot.parts == ("response", "status")

    def test_head_property(self) -> None:
        dot = DotAccess(parts=("a", "b", "c"), span=_SPAN)
        assert dot.head == "a"

    def test_tail_property(self) -> None:
        dot = DotAccess(parts=("a", "b", "c"), span=_SPAN)
        assert dot.tail == ("b", "c")


class TestBinaryOpExpr:
    def test_creation(self) -> None:
        left = Identifier(name="x", span=_SPAN)
        right = NumberLit(value=1.0, span=_SPAN)
        expr = BinaryOpExpr(op=BinOp.EQ, left=left, right=right, span=_SPAN)
        assert expr.op is BinOp.EQ
        assert expr.left is left
        assert expr.right is right


class TestUnaryOpExpr:
    def test_creation(self) -> None:
        operand = Identifier(name="flagged", span=_SPAN)
        expr = UnaryOpExpr(op=UnaryOpKind.NOT, operand=operand, span=_SPAN)
        assert expr.op is UnaryOpKind.NOT
        assert expr.operand is operand


class TestFunctionCall:
    def test_creation_no_args(self) -> None:
        call = FunctionCall(name="len", arguments=(), span=_SPAN)
        assert call.name == "len"
        assert call.arguments == ()

    def test_creation_with_args(self) -> None:
        arg = Identifier(name="items", span=_SPAN)
        call = FunctionCall(name="len", arguments=(arg,), span=_SPAN)
        assert len(call.arguments) == 1


class TestContainsExpr:
    def test_creation(self) -> None:
        subject = Identifier(name="response", span=_SPAN)
        value = StringLit(value="error", span=_SPAN)
        expr = ContainsExpr(subject=subject, value=value, span=_SPAN)
        assert expr.subject is subject
        assert expr.value is value


class TestInListExpr:
    def test_creation(self) -> None:
        subject = Identifier(name="status", span=_SPAN)
        items = (NumberLit(value=200.0, span=_SPAN), NumberLit(value=201.0, span=_SPAN))
        expr = InListExpr(subject=subject, items=items, span=_SPAN)
        assert len(expr.items) == 2


class TestBeforeExpr:
    def test_creation(self) -> None:
        left = Identifier(name="a", span=_SPAN)
        right = Identifier(name="b", span=_SPAN)
        expr = BeforeExpr(left=left, right=right, span=_SPAN)
        assert expr.left is left
        assert expr.right is right


class TestAfterExpr:
    def test_creation(self) -> None:
        left = Identifier(name="a", span=_SPAN)
        right = Identifier(name="b", span=_SPAN)
        expr = AfterExpr(left=left, right=right, span=_SPAN)
        assert expr.left is left
        assert expr.right is right


# ---------------------------------------------------------------------------
# Constraint nodes
# ---------------------------------------------------------------------------


class TestConstraint:
    def test_creation(self) -> None:
        expr = Identifier(name="safe", span=_SPAN)
        constraint = Constraint(expression=expr, span=_SPAN)
        assert constraint.expression is expr


class TestShouldConstraint:
    def test_creation_without_percentage(self) -> None:
        expr = Identifier(name="polite", span=_SPAN)
        c = ShouldConstraint(expression=expr, percentage=None, span=_SPAN)
        assert c.percentage is None

    def test_creation_with_percentage(self) -> None:
        expr = Identifier(name="polite", span=_SPAN)
        c = ShouldConstraint(expression=expr, percentage=80.0, span=_SPAN)
        assert c.percentage == 80.0


class TestThresholdClause:
    def test_creation(self) -> None:
        t = ThresholdClause(operator="<", value=500.0, is_percentage=False, span=_SPAN)
        assert t.operator == "<"
        assert t.value == 500.0
        assert t.is_percentage is False

    def test_percentage_threshold(self) -> None:
        t = ThresholdClause(operator=">=", value=95.0, is_percentage=True, span=_SPAN)
        assert t.is_percentage is True


class TestEscalationClause:
    def test_creation(self) -> None:
        cond = Identifier(name="user_angry", span=_SPAN)
        esc = EscalationClause(condition=cond, span=_SPAN)
        assert esc.condition is cond


# ---------------------------------------------------------------------------
# Behavior and Invariant
# ---------------------------------------------------------------------------


def _make_behavior(name: str = "greet") -> Behavior:
    return Behavior(
        name=name,
        when_clause=None,
        must_constraints=(),
        must_not_constraints=(),
        should_constraints=(),
        may_constraints=(),
        confidence=None,
        latency=None,
        cost=None,
        escalation=None,
        audit=AuditLevel.NONE,
        span=_SPAN,
    )


def _make_invariant(name: str = "safety") -> Invariant:
    return Invariant(
        name=name,
        constraints=(),
        prohibitions=(),
        applies_to=AppliesTo.ALL_BEHAVIORS,
        named_behaviors=(),
        severity=Severity.HIGH,
        span=_SPAN,
    )


def _make_spec(
    name: str = "TestAgent",
    behaviors: tuple[Behavior, ...] = (),
    invariants: tuple[Invariant, ...] = (),
) -> AgentSpec:
    return AgentSpec(
        name=name,
        version=None,
        model=None,
        owner=None,
        behaviors=behaviors,
        invariants=invariants,
        degradations=(),
        compositions=(),
        span=_SPAN,
    )


class TestBehavior:
    def test_minimal_behavior_creation(self) -> None:
        b = _make_behavior("answer")
        assert b.name == "answer"
        assert b.when_clause is None
        assert b.audit is AuditLevel.NONE

    def test_behavior_must_constraints_tuple(self) -> None:
        expr = Identifier(name="safe", span=_SPAN)
        c = Constraint(expression=expr, span=_SPAN)
        b = Behavior(
            name="respond",
            when_clause=None,
            must_constraints=(c,),
            must_not_constraints=(),
            should_constraints=(),
            may_constraints=(),
            confidence=None,
            latency=None,
            cost=None,
            escalation=None,
            audit=AuditLevel.NONE,
            span=_SPAN,
        )
        assert len(b.must_constraints) == 1


class TestInvariant:
    def test_minimal_invariant_creation(self) -> None:
        inv = _make_invariant("global_rule")
        assert inv.name == "global_rule"
        assert inv.applies_to is AppliesTo.ALL_BEHAVIORS
        assert inv.severity is Severity.HIGH


# ---------------------------------------------------------------------------
# AgentSpec
# ---------------------------------------------------------------------------


class TestAgentSpec:
    def test_get_behavior_found(self) -> None:
        b = _make_behavior("greet")
        spec = _make_spec(behaviors=(b,))
        result = spec.get_behavior("greet")
        assert result is b

    def test_get_behavior_not_found_returns_none(self) -> None:
        spec = _make_spec()
        assert spec.get_behavior("nonexistent") is None

    def test_get_invariant_found(self) -> None:
        inv = _make_invariant("safety")
        spec = _make_spec(invariants=(inv,))
        result = spec.get_invariant("safety")
        assert result is inv

    def test_get_invariant_not_found_returns_none(self) -> None:
        spec = _make_spec()
        assert spec.get_invariant("ghost") is None

    def test_behavior_names_is_sorted(self) -> None:
        b1 = _make_behavior("zebra")
        b2 = _make_behavior("alpha")
        b3 = _make_behavior("mango")
        spec = _make_spec(behaviors=(b1, b2, b3))
        assert spec.behavior_names == ["alpha", "mango", "zebra"]

    def test_invariant_names_is_sorted(self) -> None:
        i1 = _make_invariant("z_rule")
        i2 = _make_invariant("a_rule")
        spec = _make_spec(invariants=(i1, i2))
        assert spec.invariant_names == ["a_rule", "z_rule"]

    def test_behavior_names_empty_when_no_behaviors(self) -> None:
        spec = _make_spec()
        assert spec.behavior_names == []


# ---------------------------------------------------------------------------
# Composition nodes
# ---------------------------------------------------------------------------


class TestReceives:
    def test_creation(self) -> None:
        r = Receives(source_agent="InputAgent", span=_SPAN)
        assert r.source_agent == "InputAgent"


class TestDelegates:
    def test_creation(self) -> None:
        d = Delegates(target_agent="ChildAgent", span=_SPAN)
        assert d.target_agent == "ChildAgent"


class TestDegradation:
    def test_creation(self) -> None:
        cond = Identifier(name="overloaded", span=_SPAN)
        deg = Degradation(fallback="FallbackAgent", condition=cond, span=_SPAN)
        assert deg.fallback == "FallbackAgent"
        assert deg.condition is cond
