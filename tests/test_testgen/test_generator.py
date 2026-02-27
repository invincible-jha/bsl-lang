"""Tests for bsl.testgen.generator — ComplianceTestGenerator."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from bsl.ast.nodes import (
    AgentSpec,
    AppliesTo,
    AuditLevel,
    Behavior,
    Composition,
    Constraint,
    Degradation,
    EscalationClause,
    Identifier,
    Invariant,
    Severity,
    ShouldConstraint,
    Span,
    ThresholdClause,
)
from bsl.testgen.generator import (
    ComplianceTestGenerator,
    GeneratedTest,
    TestGenConfig,
    TestGenResult,
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


def _threshold(op: str, value: float) -> ThresholdClause:
    return ThresholdClause(operator=op, value=value, is_percentage=False, span=_S)


def _escalation(cond: str) -> EscalationClause:
    return EscalationClause(condition=_ident(cond), span=_S)


def _behavior(
    name: str,
    *,
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
        when_clause=None,
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
    constraints: tuple[Constraint, ...] = (),
    prohibitions: tuple[Constraint, ...] = (),
) -> Invariant:
    return Invariant(
        name=name,
        constraints=constraints,
        prohibitions=prohibitions,
        applies_to=AppliesTo.ALL_BEHAVIORS,
        named_behaviors=(),
        severity=severity,
        span=_S,
    )


def _spec(
    name: str = "TestAgent",
    *,
    behaviors: tuple[Behavior, ...] = (),
    invariants: tuple[Invariant, ...] = (),
) -> AgentSpec:
    return AgentSpec(
        name=name,
        version="1.0.0",
        model="gpt-4o",
        owner="team",
        behaviors=behaviors,
        invariants=invariants,
        degradations=(),
        compositions=(),
        span=_S,
    )


# ===========================================================================
# TestGenConfig
# ===========================================================================


class TestTestGenConfig:
    def test_defaults(self) -> None:
        config = TestGenConfig()
        assert config.include_invariants is True
        assert config.include_behaviors is True
        assert config.include_thresholds is True
        assert config.include_escalation is True
        assert config.include_audit is False
        assert config.fixture_name == "agent_context"

    def test_custom_fixture_name(self) -> None:
        config = TestGenConfig(fixture_name="my_agent")
        assert config.fixture_name == "my_agent"

    def test_disable_invariants(self) -> None:
        config = TestGenConfig(include_invariants=False)
        assert not config.include_invariants


# ===========================================================================
# GeneratedTest
# ===========================================================================


class TestGeneratedTest:
    def test_frozen(self) -> None:
        test = GeneratedTest(
            function_name="test_foo",
            source="def test_foo(): pass",
            origin_kind="invariant",
            origin_name="foo",
            description="foo",
        )
        with pytest.raises((AttributeError, TypeError)):
            test.function_name = "other"  # type: ignore[misc]

    def test_defaults(self) -> None:
        test = GeneratedTest(
            function_name="test_foo",
            source="def test_foo(): pass",
            origin_kind="invariant",
            origin_name="foo",
            description="foo",
        )
        assert test.skip_reason == ""


# ===========================================================================
# TestGenResult
# ===========================================================================


class TestTestGenResult:
    def _make_result(self, tests: list[GeneratedTest]) -> TestGenResult:
        return TestGenResult(agent_name="MyAgent", tests=tests)

    def test_test_count(self) -> None:
        tests = [
            GeneratedTest("t1", "src", "invariant", "inv", "d"),
            GeneratedTest("t2", "src", "behavior_must", "beh", "d"),
        ]
        result = self._make_result(tests)
        assert result.test_count == 2

    def test_skipped_count(self) -> None:
        tests = [
            GeneratedTest("t1", "src", "invariant", "inv", "d", skip_reason="skip me"),
            GeneratedTest("t2", "src", "behavior_must", "beh", "d"),
        ]
        result = self._make_result(tests)
        assert result.skipped_count == 1

    def test_by_kind(self) -> None:
        tests = [
            GeneratedTest("t1", "src", "invariant", "inv1", "d"),
            GeneratedTest("t2", "src", "invariant", "inv2", "d"),
            GeneratedTest("t3", "src", "behavior_must", "beh", "d"),
        ]
        result = self._make_result(tests)
        assert len(result.by_kind("invariant")) == 2
        assert len(result.by_kind("behavior_must")) == 1
        assert len(result.by_kind("unknown")) == 0

    def test_render_empty(self) -> None:
        result = self._make_result([])
        rendered = result.render()
        assert "MyAgent" in rendered
        assert "import pytest" in rendered
        assert "No tests generated" in rendered

    def test_render_includes_fixture(self) -> None:
        result = self._make_result([])
        rendered = result.render()
        assert "@pytest.fixture()" in rendered
        assert "def agent_context():" in rendered

    def test_render_includes_test_function(self) -> None:
        tests = [
            GeneratedTest(
                "test_inv_must_0",
                "def test_inv_must_0(agent_context):\n    assert True",
                "invariant",
                "inv",
                "desc",
            )
        ]
        result = self._make_result(tests)
        rendered = result.render()
        assert "def test_inv_must_0" in rendered

    def test_render_includes_section_headers(self) -> None:
        tests = [
            GeneratedTest("t1", "def t1(): pass", "invariant", "inv", "d"),
            GeneratedTest("t2", "def t2(): pass", "behavior_must", "beh", "d"),
        ]
        result = self._make_result(tests)
        rendered = result.render()
        assert "Section:" in rendered

    def test_write_creates_file(self, tmp_path: Path) -> None:
        tests = [
            GeneratedTest(
                "test_foo", "def test_foo(agent_context): pass", "invariant", "foo", "d"
            )
        ]
        result = self._make_result(tests)
        output_file = tmp_path / "out" / "test_compliance.py"
        written_path = result.write(output_file)
        assert written_path == output_file
        assert output_file.exists()
        content = output_file.read_text()
        assert "test_foo" in content


# ===========================================================================
# ComplianceTestGenerator
# ===========================================================================


class TestComplianceTestGeneratorBasic:
    def setup_method(self) -> None:
        self.gen = ComplianceTestGenerator()

    def test_empty_spec_produces_no_tests(self) -> None:
        spec = _spec()
        result = self.gen.generate(spec)
        assert result.test_count == 0

    def test_returns_test_gen_result(self) -> None:
        spec = _spec()
        result = self.gen.generate(spec)
        assert isinstance(result, TestGenResult)

    def test_agent_name_captured(self) -> None:
        spec = _spec("SupportBot")
        result = self.gen.generate(spec)
        assert result.agent_name == "SupportBot"

    def test_generated_at_set(self) -> None:
        spec = _spec()
        result = self.gen.generate(spec)
        assert result.generated_at  # non-empty ISO string


class TestComplianceTestGeneratorInvariants:
    def setup_method(self) -> None:
        self.gen = ComplianceTestGenerator()

    def test_invariant_constraint_produces_test(self) -> None:
        inv = _invariant("safety", constraints=(_constraint("safe"),))
        spec = _spec(invariants=(inv,))
        result = self.gen.generate(spec)
        invariant_tests = result.by_kind("invariant")
        assert len(invariant_tests) == 1
        assert "safety" in invariant_tests[0].function_name
        assert invariant_tests[0].origin_name == "safety"

    def test_invariant_prohibition_produces_test(self) -> None:
        inv = _invariant("safety", prohibitions=(_constraint("harmful"),))
        spec = _spec(invariants=(inv,))
        result = self.gen.generate(spec)
        invariant_tests = result.by_kind("invariant")
        assert len(invariant_tests) == 1
        assert "must_not" in invariant_tests[0].function_name

    def test_multiple_invariant_constraints(self) -> None:
        inv = _invariant(
            "safety",
            constraints=(_constraint("safe"), _constraint("checked")),
            prohibitions=(_constraint("harmful"),),
        )
        spec = _spec(invariants=(inv,))
        result = self.gen.generate(spec)
        invariant_tests = result.by_kind("invariant")
        assert len(invariant_tests) == 3

    def test_two_invariants(self) -> None:
        inv1 = _invariant("safety", constraints=(_constraint("safe"),))
        inv2 = _invariant("security", constraints=(_constraint("auth"),))
        spec = _spec(invariants=(inv1, inv2))
        result = self.gen.generate(spec)
        assert result.test_count == 2

    def test_invariant_function_name_valid_python(self) -> None:
        inv = _invariant("my-invariant", constraints=(_constraint("x"),))
        spec = _spec(invariants=(inv,))
        result = self.gen.generate(spec)
        fname = result.tests[0].function_name
        # Must be a valid Python identifier starting with test_
        assert fname.startswith("test_")
        assert fname.isidentifier()

    def test_severity_reflected_in_docstring(self) -> None:
        inv = _invariant(
            "safety", severity=Severity.CRITICAL, constraints=(_constraint("x"),)
        )
        spec = _spec(invariants=(inv,))
        result = self.gen.generate(spec)
        source = result.tests[0].source
        assert "CRITICAL" in source

    def test_invariants_disabled(self) -> None:
        config = TestGenConfig(include_invariants=False)
        gen = ComplianceTestGenerator(config)
        inv = _invariant("safety", constraints=(_constraint("safe"),))
        spec = _spec(invariants=(inv,))
        result = gen.generate(spec)
        assert result.test_count == 0


class TestComplianceTestGeneratorBehaviors:
    def setup_method(self) -> None:
        self.gen = ComplianceTestGenerator()

    def test_must_constraint_produces_test(self) -> None:
        beh = _behavior("respond", must=(_constraint("safe"),))
        spec = _spec(behaviors=(beh,))
        result = self.gen.generate(spec)
        must_tests = result.by_kind("behavior_must")
        assert len(must_tests) == 1
        assert "respond" in must_tests[0].function_name

    def test_must_not_constraint_produces_test(self) -> None:
        beh = _behavior("respond", must_not=(_constraint("harmful"),))
        spec = _spec(behaviors=(beh,))
        result = self.gen.generate(spec)
        must_not_tests = result.by_kind("behavior_must_not")
        assert len(must_not_tests) == 1

    def test_should_constraint_produces_skipped_test(self) -> None:
        beh = _behavior("respond", should=(_should("polite"),))
        spec = _spec(behaviors=(beh,))
        result = self.gen.generate(spec)
        should_tests = result.by_kind("behavior_should")
        assert len(should_tests) == 1
        assert should_tests[0].skip_reason
        assert "pytest.skip" in should_tests[0].source

    def test_may_constraint_produces_test(self) -> None:
        beh = _behavior("respond", may=(_constraint("suggest"),))
        spec = _spec(behaviors=(beh,))
        result = self.gen.generate(spec)
        may_tests = result.by_kind("behavior_may")
        assert len(may_tests) == 1

    def test_confidence_threshold_produces_test(self) -> None:
        beh = _behavior("respond", confidence=_threshold(">=", 0.9))
        spec = _spec(behaviors=(beh,))
        result = self.gen.generate(spec)
        thresh_tests = result.by_kind("behavior_threshold")
        assert len(thresh_tests) == 1
        assert "confidence" in thresh_tests[0].function_name

    def test_latency_and_cost_thresholds(self) -> None:
        beh = _behavior(
            "respond",
            latency=_threshold("<", 500.0),
            cost=_threshold("<", 0.01),
        )
        spec = _spec(behaviors=(beh,))
        result = self.gen.generate(spec)
        thresh_tests = result.by_kind("behavior_threshold")
        assert len(thresh_tests) == 2
        names = {t.function_name for t in thresh_tests}
        assert any("latency" in n for n in names)
        assert any("cost" in n for n in names)

    def test_escalation_produces_test(self) -> None:
        beh = _behavior("respond", escalation=_escalation("angry"))
        spec = _spec(behaviors=(beh,))
        result = self.gen.generate(spec)
        esc_tests = result.by_kind("behavior_escalation")
        assert len(esc_tests) == 1
        assert "angry" in esc_tests[0].source

    def test_audit_disabled_by_default(self) -> None:
        beh = _behavior("respond", audit=AuditLevel.FULL_TRACE)
        spec = _spec(behaviors=(beh,))
        result = self.gen.generate(spec)
        audit_tests = result.by_kind("behavior_audit")
        assert len(audit_tests) == 0

    def test_audit_enabled_in_config(self) -> None:
        config = TestGenConfig(include_audit=True)
        gen = ComplianceTestGenerator(config)
        beh = _behavior("respond", audit=AuditLevel.FULL_TRACE)
        spec = _spec(behaviors=(beh,))
        result = gen.generate(spec)
        audit_tests = result.by_kind("behavior_audit")
        assert len(audit_tests) == 1

    def test_behaviors_disabled(self) -> None:
        config = TestGenConfig(include_behaviors=False)
        gen = ComplianceTestGenerator(config)
        beh = _behavior("respond", must=(_constraint("safe"),))
        spec = _spec(behaviors=(beh,))
        result = gen.generate(spec)
        assert result.test_count == 0

    def test_thresholds_disabled(self) -> None:
        config = TestGenConfig(include_thresholds=False)
        gen = ComplianceTestGenerator(config)
        beh = _behavior(
            "respond",
            must=(_constraint("safe"),),
            confidence=_threshold(">=", 0.9),
        )
        spec = _spec(behaviors=(beh,))
        result = gen.generate(spec)
        assert len(result.by_kind("behavior_threshold")) == 0
        assert len(result.by_kind("behavior_must")) == 1


class TestComplianceTestGeneratorUniqueness:
    def test_function_names_are_unique(self) -> None:
        """Two behaviors with identical names after sanitization get unique test names."""
        beh1 = _behavior("respond", must=(_constraint("a"), _constraint("b")))
        spec = _spec(behaviors=(beh1,))
        gen = ComplianceTestGenerator()
        result = gen.generate(spec)
        names = [t.function_name for t in result.tests]
        assert len(names) == len(set(names)), "Duplicate function names detected"


class TestComplianceTestGeneratorRender:
    def test_render_contains_agent_name(self) -> None:
        spec = _spec("SupportBot", behaviors=(_behavior("greet", must=(_constraint("polite"),)),))
        result = ComplianceTestGenerator().generate(spec)
        rendered = result.render()
        assert "SupportBot" in rendered

    def test_render_is_valid_python_syntax(self) -> None:
        """The rendered file must compile without SyntaxError."""
        spec = _spec(
            "MyBot",
            behaviors=(
                _behavior(
                    "respond",
                    must=(_constraint("safe"),),
                    must_not=(_constraint("harmful"),),
                    should=(_should("polite"),),
                    confidence=_threshold(">=", 0.9),
                    escalation=_escalation("angry"),
                ),
            ),
            invariants=(_invariant("safety", constraints=(_constraint("x"),)),),
        )
        result = ComplianceTestGenerator().generate(spec)
        rendered = result.render()
        # Should not raise
        compile(rendered, "<generated>", "exec")

    def test_rendered_file_contains_fixture(self) -> None:
        spec = _spec(behaviors=(_behavior("b", must=(_constraint("c"),)),))
        result = ComplianceTestGenerator().generate(spec)
        rendered = result.render()
        assert "def agent_context" in rendered

    def test_custom_fixture_name_in_render(self) -> None:
        config = TestGenConfig(fixture_name="my_fixture")
        gen = ComplianceTestGenerator(config)
        spec = _spec(behaviors=(_behavior("b", must=(_constraint("c"),)),))
        result = gen.generate(spec)
        rendered = result.render()
        assert "def my_fixture" in rendered
        assert "def test_behavior_b_must_0(my_fixture)" in rendered
