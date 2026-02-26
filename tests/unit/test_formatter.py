"""Unit tests for bsl.formatter.formatter — BslFormatter and format_spec."""
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
)
from bsl.formatter.formatter import BslFormatter, format_spec

_S = Span.unknown()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ident(name: str) -> Identifier:
    return Identifier(name=name, span=_S)


def _str_lit(value: str) -> StringLit:
    return StringLit(value=value, span=_S)


def _num_lit(value: float) -> NumberLit:
    return NumberLit(value=value, span=_S)


def _bool_lit(value: bool) -> BoolLit:
    return BoolLit(value=value, span=_S)


def _constraint(name: str) -> Constraint:
    return Constraint(expression=_ident(name), span=_S)


def _should(name: str, pct: float | None = None) -> ShouldConstraint:
    return ShouldConstraint(expression=_ident(name), percentage=pct, span=_S)


def _threshold(op: str, value: float, pct: bool = False) -> ThresholdClause:
    return ThresholdClause(operator=op, value=value, is_percentage=pct, span=_S)


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
    applies_to: AppliesTo = AppliesTo.ALL_BEHAVIORS,
    named_behaviors: tuple[str, ...] = (),
    constraints: tuple[Constraint, ...] = (),
    prohibitions: tuple[Constraint, ...] = (),
    severity: Severity = Severity.HIGH,
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
    version: str | None = None,
    model: str | None = None,
    owner: str | None = None,
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
# BslFormatter.format
# ===========================================================================


class TestBslFormatterAgentBlock:
    def setup_method(self) -> None:
        self.formatter = BslFormatter()

    def test_minimal_agent_block(self) -> None:
        spec = _spec("MinAgent")
        output = self.formatter.format(spec)
        assert output.startswith("agent MinAgent {")
        assert output.endswith("}\n")

    def test_output_ends_with_newline(self) -> None:
        output = self.formatter.format(_spec("A"))
        assert output.endswith("\n")

    def test_version_emitted_when_present(self) -> None:
        spec = _spec("A", version="2.0.0")
        output = self.formatter.format(spec)
        assert 'version: "2.0.0"' in output

    def test_model_emitted_when_present(self) -> None:
        spec = _spec("A", model="gpt-4o")
        output = self.formatter.format(spec)
        assert 'model: "gpt-4o"' in output

    def test_owner_emitted_when_present(self) -> None:
        spec = _spec("A", owner="team@example.com")
        output = self.formatter.format(spec)
        assert 'owner: "team@example.com"' in output

    def test_version_not_emitted_when_absent(self) -> None:
        spec = _spec("A", version=None)
        output = self.formatter.format(spec)
        assert "version:" not in output

    def test_model_not_emitted_when_absent(self) -> None:
        spec = _spec("A", model=None)
        output = self.formatter.format(spec)
        assert "model:" not in output

    def test_owner_not_emitted_when_absent(self) -> None:
        spec = _spec("A", owner=None)
        output = self.formatter.format(spec)
        assert "owner:" not in output


class TestBslFormatterBehavior:
    def setup_method(self) -> None:
        self.formatter = BslFormatter()

    def test_behavior_block_structure(self) -> None:
        spec = _spec("A", behaviors=(_behavior("respond"),))
        output = self.formatter.format(spec)
        assert "behavior respond {" in output

    def test_must_constraint_emitted(self) -> None:
        spec = _spec("A", behaviors=(_behavior("respond", must=(_constraint("safe"),)),))
        output = self.formatter.format(spec)
        assert "must: safe" in output

    def test_must_not_constraint_emitted(self) -> None:
        spec = _spec("A", behaviors=(_behavior("respond", must_not=(_constraint("harmful"),)),))
        output = self.formatter.format(spec)
        assert "must_not: harmful" in output

    def test_may_constraint_emitted(self) -> None:
        spec = _spec("A", behaviors=(_behavior("respond", may=(_constraint("suggest"),)),))
        output = self.formatter.format(spec)
        assert "may: suggest" in output

    def test_should_constraint_without_pct(self) -> None:
        spec = _spec("A", behaviors=(_behavior("respond", should=(_should("polite"),)),))
        output = self.formatter.format(spec)
        assert "should: polite" in output
        assert "% of cases" not in output

    def test_should_constraint_with_integer_pct(self) -> None:
        spec = _spec("A", behaviors=(_behavior("respond", should=(_should("polite", 80.0),)),))
        output = self.formatter.format(spec)
        assert "80% of cases" in output

    def test_should_constraint_with_float_pct(self) -> None:
        spec = _spec("A", behaviors=(_behavior("respond", should=(_should("polite", 80.5),)),))
        output = self.formatter.format(spec)
        assert "80.5% of cases" in output

    def test_when_clause_emitted(self) -> None:
        spec = _spec("A", behaviors=(_behavior("respond", when_clause=_ident("online")),))
        output = self.formatter.format(spec)
        assert "when: online" in output

    def test_confidence_threshold_emitted(self) -> None:
        conf = _threshold(">=", 0.9)
        spec = _spec("A", behaviors=(_behavior("respond", confidence=conf),))
        output = self.formatter.format(spec)
        assert "confidence: >=0.9" in output

    def test_confidence_threshold_percentage_emitted(self) -> None:
        conf = _threshold(">=", 90.0, pct=True)
        spec = _spec("A", behaviors=(_behavior("respond", confidence=conf),))
        output = self.formatter.format(spec)
        assert "confidence: >=90%" in output

    def test_latency_threshold_emitted(self) -> None:
        lat = _threshold("<", 500.0)
        spec = _spec("A", behaviors=(_behavior("respond", latency=lat),))
        output = self.formatter.format(spec)
        assert "latency: <500" in output

    def test_cost_threshold_emitted(self) -> None:
        cost = _threshold("<", 0.05)
        spec = _spec("A", behaviors=(_behavior("respond", cost=cost),))
        output = self.formatter.format(spec)
        assert "cost: <0.05" in output

    def test_audit_basic_emitted(self) -> None:
        spec = _spec("A", behaviors=(_behavior("respond", audit=AuditLevel.BASIC),))
        output = self.formatter.format(spec)
        assert "audit: basic" in output

    def test_audit_full_trace_emitted(self) -> None:
        spec = _spec("A", behaviors=(_behavior("respond", audit=AuditLevel.FULL_TRACE),))
        output = self.formatter.format(spec)
        assert "audit: full_trace" in output

    def test_audit_none_not_emitted(self) -> None:
        spec = _spec("A", behaviors=(_behavior("respond", audit=AuditLevel.NONE),))
        output = self.formatter.format(spec)
        assert "audit:" not in output

    def test_escalation_emitted(self) -> None:
        esc = EscalationClause(condition=_ident("angry"), span=_S)
        spec = _spec("A", behaviors=(_behavior("respond", escalation=esc),))
        output = self.formatter.format(spec)
        assert "escalate_to_human when: angry" in output


class TestBslFormatterInvariant:
    def setup_method(self) -> None:
        self.formatter = BslFormatter()

    def test_invariant_block_structure(self) -> None:
        inv = _invariant("safety", constraints=(_constraint("safe"),))
        spec = _spec("A", invariants=(inv,))
        output = self.formatter.format(spec)
        assert "invariant safety {" in output

    def test_invariant_applies_to_all_behaviors(self) -> None:
        inv = _invariant("safety", applies_to=AppliesTo.ALL_BEHAVIORS)
        spec = _spec("A", invariants=(inv,))
        output = self.formatter.format(spec)
        assert "applies_to: all_behaviors" in output

    def test_invariant_applies_to_named(self) -> None:
        inv = _invariant(
            "rule",
            applies_to=AppliesTo.NAMED,
            named_behaviors=("respond", "greet"),
        )
        spec = _spec("A", invariants=(inv,))
        output = self.formatter.format(spec)
        assert "applies_to: [respond, greet]" in output

    def test_invariant_severity_emitted(self) -> None:
        inv = _invariant("rule", severity=Severity.CRITICAL)
        spec = _spec("A", invariants=(inv,))
        output = self.formatter.format(spec)
        assert "severity: critical" in output

    def test_invariant_must_constraint_emitted(self) -> None:
        inv = _invariant("rule", constraints=(_constraint("safe"),))
        spec = _spec("A", invariants=(inv,))
        output = self.formatter.format(spec)
        assert "must: safe" in output

    def test_invariant_must_not_constraint_emitted(self) -> None:
        inv = _invariant("rule", prohibitions=(_constraint("harmful"),))
        spec = _spec("A", invariants=(inv,))
        output = self.formatter.format(spec)
        assert "must_not: harmful" in output


class TestBslFormatterDegradationAndComposition:
    def setup_method(self) -> None:
        self.formatter = BslFormatter()

    def test_degradation_emitted(self) -> None:
        deg = Degradation(fallback="fallback_beh", condition=_ident("overloaded"), span=_S)
        spec = _spec("A", degradations=(deg,))
        output = self.formatter.format(spec)
        assert "degrades_to fallback_beh when: overloaded" in output

    def test_receives_composition_emitted(self) -> None:
        rec = Receives(source_agent="InputAgent", span=_S)
        spec = _spec("A", compositions=(rec,))
        output = self.formatter.format(spec)
        assert "receives from InputAgent" in output

    def test_delegates_composition_emitted(self) -> None:
        dlg = Delegates(target_agent="ChildAgent", span=_S)
        spec = _spec("A", compositions=(dlg,))
        output = self.formatter.format(spec)
        assert "delegates_to ChildAgent" in output


class TestBslFormatterExpressions:
    def setup_method(self) -> None:
        self.formatter = BslFormatter()

    def _format_must(self, expr: object) -> str:
        spec = _spec(
            "A",
            behaviors=(_behavior("b", must=(Constraint(expression=expr, span=_S),)),),  # type: ignore[arg-type]
        )
        return self.formatter.format(spec)

    def test_identifier_expression(self) -> None:
        assert "must: safe" in self._format_must(_ident("safe"))

    def test_dot_access_expression(self) -> None:
        expr = DotAccess(parts=("response", "status"), span=_S)
        assert "must: response.status" in self._format_must(expr)

    def test_string_lit_expression(self) -> None:
        assert 'must: "hello"' in self._format_must(_str_lit("hello"))

    def test_string_lit_with_escape(self) -> None:
        output = self._format_must(_str_lit('say "hi"'))
        assert '\\"hi\\"' in output

    def test_number_lit_integer(self) -> None:
        assert "must: 42" in self._format_must(_num_lit(42.0))

    def test_number_lit_float(self) -> None:
        assert "must: 3.14" in self._format_must(_num_lit(3.14))

    def test_bool_lit_true(self) -> None:
        assert "must: true" in self._format_must(_bool_lit(True))

    def test_bool_lit_false(self) -> None:
        assert "must: false" in self._format_must(_bool_lit(False))

    def test_binary_op_eq(self) -> None:
        expr = BinaryOpExpr(op=BinOp.EQ, left=_ident("x"), right=_num_lit(1.0), span=_S)
        assert "x == 1" in self._format_must(expr)

    def test_binary_op_and(self) -> None:
        expr = BinaryOpExpr(op=BinOp.AND, left=_ident("a"), right=_ident("b"), span=_S)
        assert "a and b" in self._format_must(expr)

    def test_binary_op_or(self) -> None:
        expr = BinaryOpExpr(op=BinOp.OR, left=_ident("a"), right=_ident("b"), span=_S)
        assert "a or b" in self._format_must(expr)

    def test_binary_op_nested_and_or_gets_parens(self) -> None:
        inner = BinaryOpExpr(op=BinOp.OR, left=_ident("a"), right=_ident("b"), span=_S)
        outer = BinaryOpExpr(op=BinOp.AND, left=inner, right=_ident("c"), span=_S)
        output = self._format_must(outer)
        # inner OR should be wrapped in parens when nested under AND
        assert "(a or b)" in output

    def test_binary_op_lt(self) -> None:
        expr = BinaryOpExpr(op=BinOp.LT, left=_ident("x"), right=_num_lit(10.0), span=_S)
        assert "x < 10" in self._format_must(expr)

    def test_binary_op_contains(self) -> None:
        expr = BinaryOpExpr(op=BinOp.CONTAINS, left=_ident("text"), right=_str_lit("err"), span=_S)
        assert "contains" in self._format_must(expr)

    def test_unary_not_expression(self) -> None:
        expr = UnaryOpExpr(op=UnaryOpKind.NOT, operand=_ident("flagged"), span=_S)
        assert "not flagged" in self._format_must(expr)

    def test_function_call_no_args(self) -> None:
        expr = FunctionCall(name="check", arguments=(), span=_S)
        assert "check()" in self._format_must(expr)

    def test_function_call_with_args(self) -> None:
        expr = FunctionCall(name="len", arguments=(_ident("items"),), span=_S)
        assert "len(items)" in self._format_must(expr)

    def test_contains_expr(self) -> None:
        expr = ContainsExpr(subject=_ident("response"), value=_str_lit("error"), span=_S)
        assert 'response contains "error"' in self._format_must(expr)

    def test_in_list_expr(self) -> None:
        expr = InListExpr(
            subject=_ident("status"),
            items=(_num_lit(200.0), _num_lit(201.0)),
            span=_S,
        )
        assert "status in [200, 201]" in self._format_must(expr)

    def test_before_expr(self) -> None:
        expr = BeforeExpr(left=_ident("a"), right=_ident("b"), span=_S)
        assert "a before b" in self._format_must(expr)

    def test_after_expr(self) -> None:
        expr = AfterExpr(left=_ident("a"), right=_ident("b"), span=_S)
        assert "a after b" in self._format_must(expr)

    def test_unknown_expr_type_falls_back_to_repr(self) -> None:
        # A completely alien object — formatter should use repr() fallback
        spec = _spec(
            "A",
            behaviors=(_behavior("b", must=(Constraint(expression=42, span=_S),)),),  # type: ignore[arg-type]
        )
        # Should not raise, just include repr
        output = self.formatter.format(spec)
        assert "must:" in output


class TestFormatSpecConvenienceFunction:
    def test_returns_string(self) -> None:
        spec = _spec("A")
        result = format_spec(spec)
        assert isinstance(result, str)

    def test_produces_same_output_as_class(self) -> None:
        spec = _spec("A", version="1.0", model="gpt-4o")
        assert format_spec(spec) == BslFormatter().format(spec)

    def test_idempotent_for_simple_spec(self) -> None:
        """Formatting a spec twice should produce the same text."""
        beh = _behavior("respond", must=(_constraint("safe"),))
        inv = _invariant("safety", constraints=(_constraint("safe"),))
        spec = _spec("A", version="1.0", model="m", owner="o", behaviors=(beh,), invariants=(inv,))
        first = format_spec(spec)
        # Re-format the same spec object
        second = format_spec(spec)
        assert first == second
