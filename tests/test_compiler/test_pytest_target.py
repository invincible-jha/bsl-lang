"""Unit tests for bsl.compiler.pytest_target.

Tests verify that the PytestTarget compiles BSL ASTs into syntactically
valid Python source with the expected structure and content.
"""
from __future__ import annotations

import ast
import re

import pytest

from bsl.ast.nodes import (
    AgentSpec,
    AppliesTo,
    AuditLevel,
    Behavior,
    BinOp,
    BinaryOpExpr,
    BoolLit,
    Constraint,
    ContainsExpr,
    DotAccess,
    EscalationClause,
    Identifier,
    InListExpr,
    Invariant,
    NumberLit,
    Severity,
    ShouldConstraint,
    Span,
    StringLit,
    ThresholdClause,
    UnaryOpExpr,
    UnaryOpKind,
)
from bsl.compiler.base import CompilerOutput
from bsl.compiler.pytest_target import PytestTarget

# ---------------------------------------------------------------------------
# Test AST builders
# ---------------------------------------------------------------------------

DUMMY_SPAN = Span(start=0, end=1, line=1, col=1)


def _ident(name: str) -> Identifier:
    return Identifier(name=name, span=DUMMY_SPAN)


def _str(value: str) -> StringLit:
    return StringLit(value=value, span=DUMMY_SPAN)


def _num(value: float) -> NumberLit:
    return NumberLit(value=value, span=DUMMY_SPAN)


def _bool_lit(value: bool) -> BoolLit:
    return BoolLit(value=value, span=DUMMY_SPAN)


def _dot(*parts: str) -> DotAccess:
    return DotAccess(parts=tuple(parts), span=DUMMY_SPAN)


def _contains(subject: object, value: object) -> ContainsExpr:
    return ContainsExpr(subject=subject, value=value, span=DUMMY_SPAN)  # type: ignore[arg-type]


def _in_list(subject: object, *items: object) -> InListExpr:
    return InListExpr(subject=subject, items=tuple(items), span=DUMMY_SPAN)  # type: ignore[arg-type]


def _binop(op: BinOp, left: object, right: object) -> BinaryOpExpr:
    return BinaryOpExpr(op=op, left=left, right=right, span=DUMMY_SPAN)  # type: ignore[arg-type]


def _unary_not(operand: object) -> UnaryOpExpr:
    return UnaryOpExpr(op=UnaryOpKind.NOT, operand=operand, span=DUMMY_SPAN)  # type: ignore[arg-type]


def _constraint(expr: object) -> Constraint:
    return Constraint(expression=expr, span=DUMMY_SPAN)  # type: ignore[arg-type]


def _should_constraint(expr: object, percentage: float | None = None) -> ShouldConstraint:
    return ShouldConstraint(expression=expr, percentage=percentage, span=DUMMY_SPAN)  # type: ignore[arg-type]


def _threshold(op: str, value: float, is_percentage: bool = False) -> ThresholdClause:
    return ThresholdClause(
        operator=op, value=value, is_percentage=is_percentage, span=DUMMY_SPAN
    )


def _escalation(condition: object) -> EscalationClause:
    return EscalationClause(condition=condition, span=DUMMY_SPAN)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Minimal spec factories
# ---------------------------------------------------------------------------


def _minimal_spec(
    name: str = "TestAgent",
    behaviors: tuple[Behavior, ...] = (),
    invariants: tuple[Invariant, ...] = (),
) -> AgentSpec:
    return AgentSpec(
        name=name,
        version="1.0",
        model="gpt-4o",
        owner="test@example.com",
        behaviors=behaviors,
        invariants=invariants,
        degradations=(),
        compositions=(),
        span=DUMMY_SPAN,
    )


def _simple_behavior(
    name: str = "respond",
    must_constraints: tuple[Constraint, ...] = (),
    must_not_constraints: tuple[Constraint, ...] = (),
    should_constraints: tuple[ShouldConstraint, ...] = (),
    confidence: ThresholdClause | None = None,
    latency: ThresholdClause | None = None,
    cost: ThresholdClause | None = None,
    escalation: EscalationClause | None = None,
) -> Behavior:
    return Behavior(
        name=name,
        when_clause=None,
        must_constraints=must_constraints,
        must_not_constraints=must_not_constraints,
        should_constraints=should_constraints,
        may_constraints=(),
        confidence=confidence,
        latency=latency,
        cost=cost,
        escalation=escalation,
        audit=AuditLevel.NONE,
        span=DUMMY_SPAN,
    )


def _simple_invariant(
    name: str = "no_pii",
    constraints: tuple[Constraint, ...] = (),
    prohibitions: tuple[Constraint, ...] = (),
) -> Invariant:
    return Invariant(
        name=name,
        constraints=constraints,
        prohibitions=prohibitions,
        applies_to=AppliesTo.ALL_BEHAVIORS,
        named_behaviors=(),
        severity=Severity.CRITICAL,
        span=DUMMY_SPAN,
    )


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def target() -> PytestTarget:
    return PytestTarget()


# ---------------------------------------------------------------------------
# Basic compilation tests
# ---------------------------------------------------------------------------


class TestBasicCompilation:
    def test_compile_minimal_spec_returns_output(self, target: PytestTarget) -> None:
        spec = _minimal_spec()
        output = target.compile(spec)
        assert isinstance(output, CompilerOutput)

    def test_compile_returns_one_file(self, target: PytestTarget) -> None:
        spec = _minimal_spec()
        output = target.compile(spec)
        assert len(output.files) == 1

    def test_filename_uses_snake_case_agent_name(self, target: PytestTarget) -> None:
        spec = _minimal_spec(name="CustomerServiceAgent")
        output = target.compile(spec)
        filename = list(output.files.keys())[0]
        assert filename == "test_customer_service_agent_spec.py"

    def test_generated_source_is_valid_python(self, target: PytestTarget) -> None:
        spec = _minimal_spec()
        output = target.compile(spec)
        source = list(output.files.values())[0]
        # ast.parse raises SyntaxError on invalid Python
        ast.parse(source)

    def test_metadata_contains_agent_name(self, target: PytestTarget) -> None:
        spec = _minimal_spec(name="TestAgent")
        output = target.compile(spec)
        assert output.metadata["agent_name"] == "TestAgent"

    def test_metadata_contains_counts(self, target: PytestTarget) -> None:
        behavior = _simple_behavior(
            must_constraints=(_constraint(_contains(_ident("r"), _str("Hi"))),)
        )
        spec = _minimal_spec(behaviors=(behavior,))
        output = target.compile(spec)
        assert output.metadata["behavior_count"] == 1
        assert output.metadata["invariant_count"] == 0

    def test_target_name_is_pytest(self, target: PytestTarget) -> None:
        assert target.name == "pytest"


# ---------------------------------------------------------------------------
# Source content tests
# ---------------------------------------------------------------------------


class TestSourceContent:
    def test_header_comment_present(self, target: PytestTarget) -> None:
        spec = _minimal_spec(name="MyAgent")
        source = list(target.compile(spec).files.values())[0]
        assert "Generated by BSL compiler" in source

    def test_agent_name_in_header(self, target: PytestTarget) -> None:
        spec = _minimal_spec(name="AwesomeAgent")
        source = list(target.compile(spec).files.values())[0]
        assert "AwesomeAgent" in source

    def test_pytest_imported(self, target: PytestTarget) -> None:
        spec = _minimal_spec()
        source = list(target.compile(spec).files.values())[0]
        assert "import pytest" in source

    def test_agent_context_fixture_present(self, target: PytestTarget) -> None:
        spec = _minimal_spec()
        source = list(target.compile(spec).files.values())[0]
        assert "agent_context" in source
        assert "@pytest.fixture" in source

    def test_do_not_edit_comment_present(self, target: PytestTarget) -> None:
        spec = _minimal_spec()
        source = list(target.compile(spec).files.values())[0]
        assert "do not edit" in source.lower()


# ---------------------------------------------------------------------------
# Invariant compilation tests
# ---------------------------------------------------------------------------


class TestInvariantCompilation:
    def test_must_constraint_generates_test(self, target: PytestTarget) -> None:
        invariant = _simple_invariant(
            name="no_errors",
            constraints=(_constraint(_binop(BinOp.EQ, _ident("status"), _num(200.0))),),
        )
        spec = _minimal_spec(invariants=(invariant,))
        output = target.compile(spec)
        source = list(output.files.values())[0]
        assert "test_invariant_no_errors_must_0" in source

    def test_must_not_constraint_generates_test(self, target: PytestTarget) -> None:
        invariant = _simple_invariant(
            name="no_pii",
            prohibitions=(_constraint(_contains(_ident("response"), _str("SSN"))),),
        )
        spec = _minimal_spec(invariants=(invariant,))
        output = target.compile(spec)
        source = list(output.files.values())[0]
        assert "test_invariant_no_pii_must_not_0" in source

    def test_must_not_uses_negated_assertion(self, target: PytestTarget) -> None:
        invariant = _simple_invariant(
            name="clean",
            prohibitions=(_constraint(_contains(_ident("response"), _str("error"))),),
        )
        spec = _minimal_spec(invariants=(invariant,))
        source = list(target.compile(spec).files.values())[0]
        assert "assert not" in source

    def test_multiple_constraints_generate_multiple_tests(self, target: PytestTarget) -> None:
        invariant = _simple_invariant(
            name="multi",
            constraints=(
                _constraint(_binop(BinOp.EQ, _ident("a"), _num(1.0))),
                _constraint(_binop(BinOp.EQ, _ident("b"), _num(2.0))),
            ),
        )
        spec = _minimal_spec(invariants=(invariant,))
        output = target.compile(spec)
        source = list(output.files.values())[0]
        assert "test_invariant_multi_must_0" in source
        assert "test_invariant_multi_must_1" in source
        assert output.test_count >= 2

    def test_invariant_test_count_incremented(self, target: PytestTarget) -> None:
        invariant = _simple_invariant(
            name="pii",
            prohibitions=(
                _constraint(_contains(_ident("r"), _str("SSN"))),
                _constraint(_contains(_ident("r"), _str("CC"))),
            ),
        )
        spec = _minimal_spec(invariants=(invariant,))
        output = target.compile(spec)
        assert output.test_count == 2

    def test_empty_invariant_produces_warning(self, target: PytestTarget) -> None:
        invariant = _simple_invariant(name="empty")
        spec = _minimal_spec(invariants=(invariant,))
        output = target.compile(spec)
        assert any("empty" in w for w in output.warnings)


# ---------------------------------------------------------------------------
# Behavior compilation tests
# ---------------------------------------------------------------------------


class TestBehaviorCompilation:
    def test_must_constraint_generates_test(self, target: PytestTarget) -> None:
        behavior = _simple_behavior(
            name="greet",
            must_constraints=(_constraint(_contains(_ident("response"), _str("Hello"))),),
        )
        spec = _minimal_spec(behaviors=(behavior,))
        source = list(target.compile(spec).files.values())[0]
        assert "test_behavior_greet_must_0" in source

    def test_must_not_constraint_generates_test(self, target: PytestTarget) -> None:
        behavior = _simple_behavior(
            name="greet",
            must_not_constraints=(_constraint(_contains(_ident("response"), _str("robot"))),),
        )
        spec = _minimal_spec(behaviors=(behavior,))
        source = list(target.compile(spec).files.values())[0]
        assert "test_behavior_greet_must_not_0" in source

    def test_should_constraint_generates_xfail_test(self, target: PytestTarget) -> None:
        behavior = _simple_behavior(
            name="greet",
            should_constraints=(
                _should_constraint(
                    _binop(BinOp.EQ, _dot("response", "tone"), _str("warm")),
                    percentage=90.0,
                ),
            ),
        )
        spec = _minimal_spec(behaviors=(behavior,))
        source = list(target.compile(spec).files.values())[0]
        assert "test_behavior_greet_should_0" in source
        assert "xfail" in source

    def test_confidence_threshold_generates_test(self, target: PytestTarget) -> None:
        behavior = _simple_behavior(
            name="classify",
            confidence=_threshold(">=", 90.0, is_percentage=True),
        )
        spec = _minimal_spec(behaviors=(behavior,))
        source = list(target.compile(spec).files.values())[0]
        assert "test_behavior_classify_confidence_threshold" in source

    def test_latency_threshold_generates_test(self, target: PytestTarget) -> None:
        behavior = _simple_behavior(
            name="classify",
            latency=_threshold("<", 500.0),
        )
        spec = _minimal_spec(behaviors=(behavior,))
        source = list(target.compile(spec).files.values())[0]
        assert "test_behavior_classify_latency_threshold" in source

    def test_cost_threshold_generates_test(self, target: PytestTarget) -> None:
        behavior = _simple_behavior(
            name="classify",
            cost=_threshold("<", 0.05),
        )
        spec = _minimal_spec(behaviors=(behavior,))
        source = list(target.compile(spec).files.values())[0]
        assert "test_behavior_classify_cost_threshold" in source

    def test_escalation_generates_test(self, target: PytestTarget) -> None:
        behavior = _simple_behavior(
            name="refund",
            escalation=_escalation(
                _binop(BinOp.GT, _dot("refund", "amount"), _num(500.0))
            ),
        )
        spec = _minimal_spec(behaviors=(behavior,))
        source = list(target.compile(spec).files.values())[0]
        assert "test_behavior_refund_escalation_triggered" in source

    def test_test_count_sums_all_constraint_types(self, target: PytestTarget) -> None:
        behavior = _simple_behavior(
            name="complex",
            must_constraints=(_constraint(_contains(_ident("r"), _str("ok"))),),
            must_not_constraints=(_constraint(_contains(_ident("r"), _str("fail"))),),
            should_constraints=(_should_constraint(_contains(_ident("r"), _str("good"))),),
            confidence=_threshold(">=", 80.0, is_percentage=True),
            latency=_threshold("<", 1000.0),
        )
        spec = _minimal_spec(behaviors=(behavior,))
        output = target.compile(spec)
        # must(1) + must_not(1) + should(1) + confidence(1) + latency(1) = 5
        assert output.test_count == 5


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_identical_spec_produces_identical_output(self, target: PytestTarget) -> None:
        spec = _minimal_spec(
            behaviors=(
                _simple_behavior(
                    name="greet",
                    must_constraints=(_constraint(_contains(_ident("r"), _str("Hello"))),),
                ),
            )
        )
        output1 = target.compile(spec)
        output2 = target.compile(spec)
        # Strip timestamp line before comparing (timestamps differ).
        def strip_ts(src: str) -> str:
            return re.sub(r"# Generated at.*", "", src)

        for filename in output1.files:
            assert strip_ts(output1.files[filename]) == strip_ts(output2.files[filename])

    def test_test_count_is_stable(self, target: PytestTarget) -> None:
        spec = _minimal_spec(
            invariants=(
                _simple_invariant(
                    name="stable",
                    constraints=(_constraint(_binop(BinOp.EQ, _ident("x"), _num(1.0))),),
                ),
            )
        )
        counts = [target.compile(spec).test_count for _ in range(3)]
        assert len(set(counts)) == 1


# ---------------------------------------------------------------------------
# Generated code is valid Python
# ---------------------------------------------------------------------------


class TestGeneratedCodeValidity:
    def test_invariant_with_contains_is_valid_python(self, target: PytestTarget) -> None:
        invariant = _simple_invariant(
            name="pii",
            prohibitions=(_constraint(_contains(_ident("response"), _str("SSN"))),),
        )
        spec = _minimal_spec(invariants=(invariant,))
        source = list(target.compile(spec).files.values())[0]
        ast.parse(source)  # raises SyntaxError if invalid

    def test_behavior_with_threshold_is_valid_python(self, target: PytestTarget) -> None:
        behavior = _simple_behavior(
            name="fast",
            confidence=_threshold(">=", 90.0, is_percentage=True),
            latency=_threshold("<", 500.0),
            cost=_threshold("<", 0.05),
        )
        spec = _minimal_spec(behaviors=(behavior,))
        source = list(target.compile(spec).files.values())[0]
        ast.parse(source)

    def test_complex_spec_is_valid_python(self, target: PytestTarget) -> None:
        behavior = _simple_behavior(
            name="handle",
            must_constraints=(
                _constraint(_contains(_ident("response"), _str("resolution"))),
            ),
            must_not_constraints=(
                _constraint(_contains(_ident("response"), _str("fault"))),
            ),
            should_constraints=(
                _should_constraint(_binop(BinOp.GTE, _dot("r", "score"), _num(0.8))),
            ),
        )
        invariant = _simple_invariant(
            name="safe",
            constraints=(_constraint(_binop(BinOp.EQ, _dot("response", "lang"), _str("en"))),),
            prohibitions=(_constraint(_contains(_ident("response"), _str("profanity"))),),
        )
        spec = _minimal_spec(behaviors=(behavior,), invariants=(invariant,))
        source = list(target.compile(spec).files.values())[0]
        ast.parse(source)
