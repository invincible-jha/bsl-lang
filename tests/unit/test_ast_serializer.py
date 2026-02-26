"""Unit tests for bsl.ast.serializer — AstSerializer round-trip tests and
all individual serialization paths to reach 85%+ coverage.
"""
from __future__ import annotations

import json

import pytest
import yaml

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
from bsl.ast.serializer import AstSerializer

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


def _minimal_behavior(name: str = "respond") -> Behavior:
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
        span=_S,
    )


def _minimal_invariant(name: str = "safety") -> Invariant:
    return Invariant(
        name=name,
        constraints=(),
        prohibitions=(),
        applies_to=AppliesTo.ALL_BEHAVIORS,
        named_behaviors=(),
        severity=Severity.HIGH,
        span=_S,
    )


def _minimal_spec(name: str = "TestAgent") -> AgentSpec:
    return AgentSpec(
        name=name,
        version=None,
        model=None,
        owner=None,
        behaviors=(),
        invariants=(),
        degradations=(),
        compositions=(),
        span=_S,
    )


# ===========================================================================
# to_dict / from_dict round-trips — minimal spec
# ===========================================================================


class TestAstSerializerMinimalSpec:
    def setup_method(self) -> None:
        self.s = AstSerializer()

    def test_to_dict_kind_is_agent_spec(self) -> None:
        data = self.s.to_dict(_minimal_spec())
        assert data["kind"] == "AgentSpec"

    def test_to_dict_name(self) -> None:
        data = self.s.to_dict(_minimal_spec("MyAgent"))
        assert data["name"] == "MyAgent"

    def test_to_dict_version_none(self) -> None:
        data = self.s.to_dict(_minimal_spec())
        assert data["version"] is None

    def test_to_dict_span_structure(self) -> None:
        data = self.s.to_dict(_minimal_spec())
        span = data["span"]
        assert "start" in span and "end" in span and "line" in span and "col" in span

    def test_round_trip_minimal_spec(self) -> None:
        spec = _minimal_spec("RoundTripAgent")
        data = self.s.to_dict(spec)
        restored = self.s.from_dict(data)
        assert restored.name == spec.name
        assert restored.version == spec.version
        assert restored.model == spec.model
        assert restored.owner == spec.owner

    def test_round_trip_with_metadata(self) -> None:
        spec = AgentSpec(
            name="MetaAgent",
            version="2.0.0",
            model="gpt-4o",
            owner="team@example.com",
            behaviors=(),
            invariants=(),
            degradations=(),
            compositions=(),
            span=_S,
        )
        data = self.s.to_dict(spec)
        restored = self.s.from_dict(data)
        assert restored.version == "2.0.0"
        assert restored.model == "gpt-4o"
        assert restored.owner == "team@example.com"


# ===========================================================================
# Behavior serialization
# ===========================================================================


class TestBehaviorSerialization:
    def setup_method(self) -> None:
        self.s = AstSerializer()

    def _round_trip_behavior(self, behavior: Behavior) -> Behavior:
        spec = AgentSpec(
            name="A",
            version=None,
            model=None,
            owner=None,
            behaviors=(behavior,),
            invariants=(),
            degradations=(),
            compositions=(),
            span=_S,
        )
        data = self.s.to_dict(spec)
        restored = self.s.from_dict(data)
        return restored.behaviors[0]

    def test_minimal_behavior_round_trip(self) -> None:
        b = _minimal_behavior("greet")
        restored = self._round_trip_behavior(b)
        assert restored.name == "greet"
        assert restored.audit == AuditLevel.NONE

    def test_behavior_with_must_constraints(self) -> None:
        b = Behavior(
            name="b",
            when_clause=None,
            must_constraints=(_constraint("safe"),),
            must_not_constraints=(),
            should_constraints=(),
            may_constraints=(),
            confidence=None,
            latency=None,
            cost=None,
            escalation=None,
            audit=AuditLevel.NONE,
            span=_S,
        )
        restored = self._round_trip_behavior(b)
        assert len(restored.must_constraints) == 1

    def test_behavior_with_must_not_constraints(self) -> None:
        b = Behavior(
            name="b",
            when_clause=None,
            must_constraints=(),
            must_not_constraints=(_constraint("harmful"),),
            should_constraints=(),
            may_constraints=(),
            confidence=None,
            latency=None,
            cost=None,
            escalation=None,
            audit=AuditLevel.NONE,
            span=_S,
        )
        restored = self._round_trip_behavior(b)
        assert len(restored.must_not_constraints) == 1

    def test_behavior_with_should_constraint_with_pct(self) -> None:
        b = Behavior(
            name="b",
            when_clause=None,
            must_constraints=(),
            must_not_constraints=(),
            should_constraints=(_should("polite", 80.0),),
            may_constraints=(),
            confidence=None,
            latency=None,
            cost=None,
            escalation=None,
            audit=AuditLevel.NONE,
            span=_S,
        )
        restored = self._round_trip_behavior(b)
        assert restored.should_constraints[0].percentage == 80.0

    def test_behavior_with_may_constraint(self) -> None:
        b = Behavior(
            name="b",
            when_clause=None,
            must_constraints=(),
            must_not_constraints=(),
            should_constraints=(),
            may_constraints=(_constraint("suggest"),),
            confidence=None,
            latency=None,
            cost=None,
            escalation=None,
            audit=AuditLevel.NONE,
            span=_S,
        )
        restored = self._round_trip_behavior(b)
        assert len(restored.may_constraints) == 1

    def test_behavior_with_confidence_threshold(self) -> None:
        conf = _threshold(">=", 0.9, pct=False)
        b = Behavior(
            name="b",
            when_clause=None,
            must_constraints=(),
            must_not_constraints=(),
            should_constraints=(),
            may_constraints=(),
            confidence=conf,
            latency=None,
            cost=None,
            escalation=None,
            audit=AuditLevel.NONE,
            span=_S,
        )
        restored = self._round_trip_behavior(b)
        assert restored.confidence is not None
        assert restored.confidence.value == pytest.approx(0.9)
        assert restored.confidence.operator == ">="

    def test_behavior_with_latency_threshold(self) -> None:
        lat = _threshold("<", 500.0)
        b = Behavior(
            name="b",
            when_clause=None,
            must_constraints=(),
            must_not_constraints=(),
            should_constraints=(),
            may_constraints=(),
            confidence=None,
            latency=lat,
            cost=None,
            escalation=None,
            audit=AuditLevel.NONE,
            span=_S,
        )
        restored = self._round_trip_behavior(b)
        assert restored.latency is not None
        assert restored.latency.value == 500.0

    def test_behavior_with_cost_threshold(self) -> None:
        cost = _threshold("<", 0.05)
        b = Behavior(
            name="b",
            when_clause=None,
            must_constraints=(),
            must_not_constraints=(),
            should_constraints=(),
            may_constraints=(),
            confidence=None,
            latency=None,
            cost=cost,
            escalation=None,
            audit=AuditLevel.NONE,
            span=_S,
        )
        restored = self._round_trip_behavior(b)
        assert restored.cost is not None
        assert restored.cost.value == pytest.approx(0.05)

    def test_behavior_with_escalation(self) -> None:
        esc = EscalationClause(condition=_ident("angry"), span=_S)
        b = Behavior(
            name="b",
            when_clause=None,
            must_constraints=(),
            must_not_constraints=(),
            should_constraints=(),
            may_constraints=(),
            confidence=None,
            latency=None,
            cost=None,
            escalation=esc,
            audit=AuditLevel.NONE,
            span=_S,
        )
        restored = self._round_trip_behavior(b)
        assert restored.escalation is not None

    def test_behavior_with_audit_basic(self) -> None:
        b = Behavior(
            name="b",
            when_clause=None,
            must_constraints=(),
            must_not_constraints=(),
            should_constraints=(),
            may_constraints=(),
            confidence=None,
            latency=None,
            cost=None,
            escalation=None,
            audit=AuditLevel.BASIC,
            span=_S,
        )
        restored = self._round_trip_behavior(b)
        assert restored.audit == AuditLevel.BASIC

    def test_behavior_with_when_clause(self) -> None:
        b = Behavior(
            name="b",
            when_clause=_ident("online"),
            must_constraints=(),
            must_not_constraints=(),
            should_constraints=(),
            may_constraints=(),
            confidence=None,
            latency=None,
            cost=None,
            escalation=None,
            audit=AuditLevel.NONE,
            span=_S,
        )
        restored = self._round_trip_behavior(b)
        assert restored.when_clause is not None


# ===========================================================================
# Invariant serialization
# ===========================================================================


class TestInvariantSerialization:
    def setup_method(self) -> None:
        self.s = AstSerializer()

    def _round_trip_invariant(self, invariant: Invariant) -> Invariant:
        spec = AgentSpec(
            name="A",
            version=None,
            model=None,
            owner=None,
            behaviors=(),
            invariants=(invariant,),
            degradations=(),
            compositions=(),
            span=_S,
        )
        data = self.s.to_dict(spec)
        restored = self.s.from_dict(data)
        return restored.invariants[0]

    def test_minimal_invariant_round_trip(self) -> None:
        inv = _minimal_invariant("safety")
        restored = self._round_trip_invariant(inv)
        assert restored.name == "safety"
        assert restored.severity == Severity.HIGH
        assert restored.applies_to == AppliesTo.ALL_BEHAVIORS

    def test_invariant_with_named_applies_to(self) -> None:
        inv = Invariant(
            name="rule",
            constraints=(_constraint("safe"),),
            prohibitions=(),
            applies_to=AppliesTo.NAMED,
            named_behaviors=("respond", "greet"),
            severity=Severity.CRITICAL,
            span=_S,
        )
        restored = self._round_trip_invariant(inv)
        assert restored.applies_to == AppliesTo.NAMED
        assert set(restored.named_behaviors) == {"respond", "greet"}
        assert restored.severity == Severity.CRITICAL

    def test_invariant_with_prohibitions(self) -> None:
        inv = Invariant(
            name="rule",
            constraints=(),
            prohibitions=(_constraint("harmful"),),
            applies_to=AppliesTo.ALL_BEHAVIORS,
            named_behaviors=(),
            severity=Severity.HIGH,
            span=_S,
        )
        restored = self._round_trip_invariant(inv)
        assert len(restored.prohibitions) == 1


# ===========================================================================
# Degradation serialization
# ===========================================================================


class TestDegradationSerialization:
    def setup_method(self) -> None:
        self.s = AstSerializer()

    def test_degradation_round_trip(self) -> None:
        deg = Degradation(fallback="fallback_beh", condition=_ident("overloaded"), span=_S)
        spec = AgentSpec(
            name="A",
            version=None,
            model=None,
            owner=None,
            behaviors=(),
            invariants=(),
            degradations=(deg,),
            compositions=(),
            span=_S,
        )
        data = self.s.to_dict(spec)
        restored = self.s.from_dict(data)
        assert restored.degradations[0].fallback == "fallback_beh"


# ===========================================================================
# Composition serialization
# ===========================================================================


class TestCompositionSerialization:
    def setup_method(self) -> None:
        self.s = AstSerializer()

    def _round_trip_compositions(self, *comps: object) -> tuple:
        spec = AgentSpec(
            name="A",
            version=None,
            model=None,
            owner=None,
            behaviors=(),
            invariants=(),
            degradations=(),
            compositions=comps,  # type: ignore[arg-type]
            span=_S,
        )
        data = self.s.to_dict(spec)
        restored = self.s.from_dict(data)
        return restored.compositions

    def test_receives_round_trip(self) -> None:
        rec = Receives(source_agent="InputAgent", span=_S)
        comps = self._round_trip_compositions(rec)
        assert isinstance(comps[0], Receives)
        assert comps[0].source_agent == "InputAgent"

    def test_delegates_round_trip(self) -> None:
        dlg = Delegates(target_agent="ChildAgent", span=_S)
        comps = self._round_trip_compositions(dlg)
        assert isinstance(comps[0], Delegates)
        assert comps[0].target_agent == "ChildAgent"

    def test_unknown_composition_type_raises_type_error(self) -> None:
        class FakeComposition:
            pass

        s = AstSerializer()
        with pytest.raises(TypeError, match="Unknown composition type"):
            s._composition_to_dict(FakeComposition())  # type: ignore[arg-type]

    def test_unknown_composition_kind_raises_value_error(self) -> None:
        s = AstSerializer()
        with pytest.raises(ValueError, match="Unknown composition kind"):
            s._composition_from_dict({"kind": "UnknownKind", "span": {"start": 0, "end": 0, "line": 0, "col": 0}})


# ===========================================================================
# Expression serialization — all expression types
# ===========================================================================


class TestExpressionSerialization:
    """Round-trip each expression type through to_dict / from_dict."""

    def setup_method(self) -> None:
        self.s = AstSerializer()

    def _round_trip_expr(self, expr: object) -> object:
        """Serialize an expr via a must-constraint and recover it."""
        c = Constraint(expression=expr, span=_S)  # type: ignore[arg-type]
        spec = AgentSpec(
            name="A",
            version=None,
            model=None,
            owner=None,
            behaviors=(Behavior(
                name="b",
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
                span=_S,
            ),),
            invariants=(),
            degradations=(),
            compositions=(),
            span=_S,
        )
        data = self.s.to_dict(spec)
        restored = self.s.from_dict(data)
        return restored.behaviors[0].must_constraints[0].expression

    def test_identifier_round_trip(self) -> None:
        expr = _ident("safe")
        restored = self._round_trip_expr(expr)
        assert isinstance(restored, Identifier)
        assert restored.name == "safe"

    def test_dot_access_round_trip(self) -> None:
        expr = DotAccess(parts=("response", "status"), span=_S)
        restored = self._round_trip_expr(expr)
        assert isinstance(restored, DotAccess)
        assert restored.parts == ("response", "status")

    def test_string_lit_round_trip(self) -> None:
        expr = _str_lit("hello world")
        restored = self._round_trip_expr(expr)
        assert isinstance(restored, StringLit)
        assert restored.value == "hello world"

    def test_number_lit_round_trip(self) -> None:
        expr = _num_lit(3.14)
        restored = self._round_trip_expr(expr)
        assert isinstance(restored, NumberLit)
        assert restored.value == pytest.approx(3.14)

    def test_bool_lit_true_round_trip(self) -> None:
        restored = self._round_trip_expr(_bool_lit(True))
        assert isinstance(restored, BoolLit)
        assert restored.value is True

    def test_bool_lit_false_round_trip(self) -> None:
        restored = self._round_trip_expr(_bool_lit(False))
        assert isinstance(restored, BoolLit)
        assert restored.value is False

    def test_binary_op_and_round_trip(self) -> None:
        expr = BinaryOpExpr(op=BinOp.AND, left=_ident("a"), right=_ident("b"), span=_S)
        restored = self._round_trip_expr(expr)
        assert isinstance(restored, BinaryOpExpr)
        assert restored.op == BinOp.AND

    def test_binary_op_eq_round_trip(self) -> None:
        expr = BinaryOpExpr(op=BinOp.EQ, left=_ident("x"), right=_num_lit(1.0), span=_S)
        restored = self._round_trip_expr(expr)
        assert isinstance(restored, BinaryOpExpr)
        assert restored.op == BinOp.EQ

    def test_unary_not_round_trip(self) -> None:
        expr = UnaryOpExpr(op=UnaryOpKind.NOT, operand=_ident("flagged"), span=_S)
        restored = self._round_trip_expr(expr)
        assert isinstance(restored, UnaryOpExpr)
        assert restored.op == UnaryOpKind.NOT

    def test_function_call_round_trip(self) -> None:
        expr = FunctionCall(name="len", arguments=(_ident("items"),), span=_S)
        restored = self._round_trip_expr(expr)
        assert isinstance(restored, FunctionCall)
        assert restored.name == "len"
        assert len(restored.arguments) == 1

    def test_contains_expr_round_trip(self) -> None:
        expr = ContainsExpr(subject=_ident("response"), value=_str_lit("error"), span=_S)
        restored = self._round_trip_expr(expr)
        assert isinstance(restored, ContainsExpr)

    def test_in_list_expr_round_trip(self) -> None:
        expr = InListExpr(
            subject=_ident("status"),
            items=(_num_lit(200.0), _num_lit(201.0)),
            span=_S,
        )
        restored = self._round_trip_expr(expr)
        assert isinstance(restored, InListExpr)
        assert len(restored.items) == 2

    def test_before_expr_round_trip(self) -> None:
        expr = BeforeExpr(left=_ident("a"), right=_ident("b"), span=_S)
        restored = self._round_trip_expr(expr)
        assert isinstance(restored, BeforeExpr)

    def test_after_expr_round_trip(self) -> None:
        expr = AfterExpr(left=_ident("a"), right=_ident("b"), span=_S)
        restored = self._round_trip_expr(expr)
        assert isinstance(restored, AfterExpr)

    def test_unknown_expr_raises_type_error(self) -> None:
        s = AstSerializer()
        with pytest.raises(TypeError, match="Unknown expression type"):
            s._expr_to_dict(42)  # type: ignore[arg-type]

    def test_unknown_expr_kind_raises_value_error(self) -> None:
        s = AstSerializer()
        with pytest.raises(ValueError, match="Unknown expression kind"):
            s._expr_from_dict({"kind": "GhostExpr", "span": {"start": 0, "end": 0, "line": 0, "col": 0}})


# ===========================================================================
# JSON serialization
# ===========================================================================


class TestJsonSerialization:
    def setup_method(self) -> None:
        self.s = AstSerializer()

    def test_to_json_returns_valid_json(self) -> None:
        spec = _minimal_spec("JsonAgent")
        json_text = self.s.to_json(spec)
        parsed = json.loads(json_text)
        assert parsed["name"] == "JsonAgent"

    def test_from_json_round_trip(self) -> None:
        spec = AgentSpec(
            name="JsonAgent",
            version="1.0",
            model="gpt-4o",
            owner="team",
            behaviors=(_minimal_behavior("greet"),),
            invariants=(_minimal_invariant("safety"),),
            degradations=(),
            compositions=(),
            span=_S,
        )
        json_text = self.s.to_json(spec)
        restored = self.s.from_json(json_text)
        assert restored.name == "JsonAgent"
        assert restored.version == "1.0"
        assert len(restored.behaviors) == 1
        assert len(restored.invariants) == 1

    def test_to_json_custom_indent(self) -> None:
        spec = _minimal_spec("A")
        json_text = self.s.to_json(spec, indent=4)
        # 4-space indented JSON will have lines starting with "    "
        lines = json_text.split("\n")
        indented = [l for l in lines if l.startswith("    ") and not l.startswith("      ")]
        assert len(indented) > 0


# ===========================================================================
# YAML serialization
# ===========================================================================


class TestYamlSerialization:
    def setup_method(self) -> None:
        self.s = AstSerializer()

    def test_to_yaml_returns_string(self) -> None:
        spec = _minimal_spec("YamlAgent")
        yaml_text = self.s.to_yaml(spec)
        assert isinstance(yaml_text, str)
        assert "YamlAgent" in yaml_text

    def test_from_yaml_round_trip(self) -> None:
        spec = AgentSpec(
            name="YamlAgent",
            version="2.0",
            model="claude-3-opus",
            owner="alice",
            behaviors=(_minimal_behavior("respond"),),
            invariants=(),
            degradations=(),
            compositions=(),
            span=_S,
        )
        yaml_text = self.s.to_yaml(spec)
        restored = self.s.from_yaml(yaml_text)
        assert restored.name == "YamlAgent"
        assert restored.version == "2.0"
        assert len(restored.behaviors) == 1

    def test_yaml_and_json_produce_same_restored_spec(self) -> None:
        beh = Behavior(
            name="greet",
            when_clause=_ident("online"),
            must_constraints=(_constraint("safe"),),
            must_not_constraints=(),
            should_constraints=(_should("polite", 80.0),),
            may_constraints=(),
            confidence=_threshold(">=", 0.9),
            latency=_threshold("<", 500.0),
            cost=None,
            escalation=None,
            audit=AuditLevel.BASIC,
            span=_S,
        )
        spec = AgentSpec(
            name="TestAgent",
            version="1.0",
            model="gpt-4o",
            owner="team@example.com",
            behaviors=(beh,),
            invariants=(),
            degradations=(),
            compositions=(),
            span=_S,
        )
        from_json = self.s.from_json(self.s.to_json(spec))
        from_yaml = self.s.from_yaml(self.s.to_yaml(spec))
        assert from_json.name == from_yaml.name
        assert from_json.version == from_yaml.version
        assert len(from_json.behaviors) == len(from_yaml.behaviors)
