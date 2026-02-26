"""Unit tests for bsl.validator.validator, bsl.validator.rules, and
bsl.validator.diagnostics — covering all three modules in one file.
"""
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
    Constraint,
    ContainsExpr,
    Degradation,
    DotAccess,
    EscalationClause,
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
)
from bsl.validator.diagnostics import Diagnostic, DiagnosticSeverity
from bsl.validator.rules import (
    DEFAULT_RULES,
    rule_conflicting_constraints,
    rule_duplicate_behaviors,
    rule_duplicate_invariants,
    rule_empty_behaviors,
    rule_missing_model,
    rule_missing_version,
    rule_percentage_range,
    rule_threshold_sanity,
    rule_undefined_applies_to,
    rule_undefined_degradation_target,
)
from bsl.validator.validator import Validator, validate

# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------

_S = Span.unknown()


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


def _threshold(op: str = ">=", value: float = 0.9, pct: bool = False) -> ThresholdClause:
    return ThresholdClause(operator=op, value=value, is_percentage=pct, span=_S)


def _behavior(
    name: str = "respond",
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
    name: str = "safety",
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
    version: str | None = "1.0.0",
    model: str | None = "gpt-4o",
    owner: str | None = "team@example.com",
    behaviors: tuple[Behavior, ...] = (),
    invariants: tuple[Invariant, ...] = (),
    degradations: tuple[Degradation, ...] = (),
) -> AgentSpec:
    return AgentSpec(
        name=name,
        version=version,
        model=model,
        owner=owner,
        behaviors=behaviors,
        invariants=invariants,
        degradations=degradations,
        compositions=(),
        span=_S,
    )


# ===========================================================================
# DiagnosticSeverity
# ===========================================================================


class TestDiagnosticSeverity:
    def test_all_levels_exist(self) -> None:
        assert DiagnosticSeverity.ERROR
        assert DiagnosticSeverity.WARNING
        assert DiagnosticSeverity.INFORMATION
        assert DiagnosticSeverity.HINT

    def test_levels_are_distinct(self) -> None:
        levels = {
            DiagnosticSeverity.ERROR,
            DiagnosticSeverity.WARNING,
            DiagnosticSeverity.INFORMATION,
            DiagnosticSeverity.HINT,
        }
        assert len(levels) == 4


# ===========================================================================
# Diagnostic dataclass
# ===========================================================================


class TestDiagnostic:
    def _make(
        self,
        severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
        code: str = "BSL001",
        message: str = "test message",
        suggestion: str | None = None,
        rule: str = "test_rule",
    ) -> Diagnostic:
        return Diagnostic(
            severity=severity,
            code=code,
            message=message,
            span=_S,
            suggestion=suggestion,
            rule=rule,
        )

    def test_is_error_true_for_error_severity(self) -> None:
        diag = self._make(severity=DiagnosticSeverity.ERROR)
        assert diag.is_error is True

    def test_is_error_false_for_warning(self) -> None:
        diag = self._make(severity=DiagnosticSeverity.WARNING)
        assert diag.is_error is False

    def test_is_error_false_for_hint(self) -> None:
        diag = self._make(severity=DiagnosticSeverity.HINT)
        assert diag.is_error is False

    def test_is_error_false_for_information(self) -> None:
        diag = self._make(severity=DiagnosticSeverity.INFORMATION)
        assert diag.is_error is False

    def test_str_contains_code_and_severity(self) -> None:
        diag = self._make(code="BSL042", severity=DiagnosticSeverity.WARNING)
        text = str(diag)
        assert "BSL042" in text
        assert "WARNING" in text

    def test_str_includes_line_and_col(self) -> None:
        span = Span(start=0, end=5, line=3, col=7)
        diag = Diagnostic(
            severity=DiagnosticSeverity.ERROR,
            code="X001",
            message="oops",
            span=span,
        )
        text = str(diag)
        assert "3:7" in text

    def test_str_includes_suggestion_when_present(self) -> None:
        diag = self._make(suggestion="Fix it like this")
        text = str(diag)
        assert "Fix it like this" in text

    def test_str_excludes_hint_section_when_no_suggestion(self) -> None:
        diag = self._make(suggestion=None)
        text = str(diag)
        assert "hint:" not in text

    def test_diagnostic_is_frozen(self) -> None:
        diag = self._make()
        with pytest.raises((AttributeError, TypeError)):
            diag.code = "CHANGED"  # type: ignore[misc]

    def test_default_suggestion_is_none(self) -> None:
        diag = Diagnostic(
            severity=DiagnosticSeverity.HINT,
            code="X",
            message="m",
            span=_S,
        )
        assert diag.suggestion is None

    def test_default_rule_is_empty_string(self) -> None:
        diag = Diagnostic(
            severity=DiagnosticSeverity.HINT,
            code="X",
            message="m",
            span=_S,
        )
        assert diag.rule == ""


# ===========================================================================
# Individual validation rules
# ===========================================================================


class TestRuleDuplicateBehaviors:
    def test_no_behaviors_returns_empty(self) -> None:
        assert rule_duplicate_behaviors(_spec()) == []

    def test_unique_behaviors_returns_empty(self) -> None:
        spec = _spec(behaviors=(_behavior("a"), _behavior("b")))
        assert rule_duplicate_behaviors(spec) == []

    def test_duplicate_behavior_raises_bsl001(self) -> None:
        spec = _spec(behaviors=(_behavior("greet"), _behavior("greet")))
        diags = rule_duplicate_behaviors(spec)
        assert len(diags) == 1
        assert diags[0].code == "BSL001"
        assert diags[0].severity == DiagnosticSeverity.ERROR
        assert "greet" in diags[0].message

    def test_three_duplicates_reports_two_errors(self) -> None:
        spec = _spec(
            behaviors=(_behavior("a"), _behavior("b"), _behavior("a"), _behavior("a"))
        )
        diags = rule_duplicate_behaviors(spec)
        assert len(diags) == 2

    def test_diagnostic_includes_first_definition_location(self) -> None:
        spec = _spec(behaviors=(_behavior("x"), _behavior("x")))
        diag = rule_duplicate_behaviors(spec)[0]
        assert "0:0" in diag.message  # Span.unknown() is line 0 col 0

    def test_suggestion_present(self) -> None:
        spec = _spec(behaviors=(_behavior("dup"), _behavior("dup")))
        diag = rule_duplicate_behaviors(spec)[0]
        assert diag.suggestion is not None


class TestRuleDuplicateInvariants:
    def test_no_invariants_returns_empty(self) -> None:
        assert rule_duplicate_invariants(_spec()) == []

    def test_unique_invariants_returns_empty(self) -> None:
        spec = _spec(invariants=(_invariant("a"), _invariant("b")))
        assert rule_duplicate_invariants(spec) == []

    def test_duplicate_invariant_raises_bsl002(self) -> None:
        spec = _spec(invariants=(_invariant("safety"), _invariant("safety")))
        diags = rule_duplicate_invariants(spec)
        assert len(diags) == 1
        assert diags[0].code == "BSL002"
        assert diags[0].severity == DiagnosticSeverity.ERROR


class TestRuleUndefinedAppliesTo:
    def test_all_behaviors_scope_skips_name_check(self) -> None:
        inv = _invariant("rule", applies_to=AppliesTo.ALL_BEHAVIORS)
        spec = _spec(invariants=(inv,))
        assert rule_undefined_applies_to(spec) == []

    def test_named_behaviors_with_valid_refs_returns_empty(self) -> None:
        behavior = _behavior("greet")
        inv = _invariant(
            "rule",
            applies_to=AppliesTo.NAMED,
            named_behaviors=("greet",),
        )
        spec = _spec(behaviors=(behavior,), invariants=(inv,))
        assert rule_undefined_applies_to(spec) == []

    def test_undefined_named_behavior_raises_bsl003(self) -> None:
        inv = _invariant(
            "rule",
            applies_to=AppliesTo.NAMED,
            named_behaviors=("ghost",),
        )
        spec = _spec(invariants=(inv,))
        diags = rule_undefined_applies_to(spec)
        assert len(diags) == 1
        assert diags[0].code == "BSL003"
        assert "ghost" in diags[0].message

    def test_multiple_undefined_refs_produce_multiple_errors(self) -> None:
        inv = _invariant(
            "rule",
            applies_to=AppliesTo.NAMED,
            named_behaviors=("missing_a", "missing_b"),
        )
        spec = _spec(invariants=(inv,))
        diags = rule_undefined_applies_to(spec)
        assert len(diags) == 2


class TestRulePercentageRange:
    def test_valid_percentage_returns_empty(self) -> None:
        should = _should("polite", 80.0)
        spec = _spec(behaviors=(_behavior("respond", should=(should,)),))
        assert rule_percentage_range(spec) == []

    def test_zero_percentage_is_valid(self) -> None:
        should = _should("polite", 0.0)
        spec = _spec(behaviors=(_behavior("respond", should=(should,)),))
        assert rule_percentage_range(spec) == []

    def test_100_percentage_is_valid(self) -> None:
        should = _should("polite", 100.0)
        spec = _spec(behaviors=(_behavior("respond", should=(should,)),))
        assert rule_percentage_range(spec) == []

    def test_negative_percentage_raises_bsl004(self) -> None:
        should = _should("polite", -1.0)
        spec = _spec(behaviors=(_behavior("respond", should=(should,)),))
        diags = rule_percentage_range(spec)
        assert len(diags) == 1
        assert diags[0].code == "BSL004"
        assert diags[0].severity == DiagnosticSeverity.ERROR

    def test_over_100_percentage_raises_bsl004(self) -> None:
        should = _should("polite", 101.0)
        spec = _spec(behaviors=(_behavior("respond", should=(should,)),))
        diags = rule_percentage_range(spec)
        assert len(diags) == 1
        assert diags[0].code == "BSL004"

    def test_none_percentage_is_skipped(self) -> None:
        should = _should("polite", None)
        spec = _spec(behaviors=(_behavior("respond", should=(should,)),))
        assert rule_percentage_range(spec) == []


class TestRuleEmptyBehaviors:
    def test_behavior_with_must_is_not_empty(self) -> None:
        spec = _spec(behaviors=(_behavior("a", must=(_constraint("x"),)),))
        assert rule_empty_behaviors(spec) == []

    def test_behavior_with_must_not_is_not_empty(self) -> None:
        spec = _spec(behaviors=(_behavior("a", must_not=(_constraint("x"),)),))
        assert rule_empty_behaviors(spec) == []

    def test_behavior_with_should_is_not_empty(self) -> None:
        spec = _spec(behaviors=(_behavior("a", should=(_should("x"),)),))
        assert rule_empty_behaviors(spec) == []

    def test_behavior_with_may_is_not_empty(self) -> None:
        spec = _spec(behaviors=(_behavior("a", may=(_constraint("x"),)),))
        assert rule_empty_behaviors(spec) == []

    def test_behavior_with_no_constraints_raises_bsl005(self) -> None:
        spec = _spec(behaviors=(_behavior("empty_beh"),))
        diags = rule_empty_behaviors(spec)
        assert len(diags) == 1
        assert diags[0].code == "BSL005"
        assert diags[0].severity == DiagnosticSeverity.WARNING

    def test_multiple_empty_behaviors_produce_multiple_warnings(self) -> None:
        spec = _spec(behaviors=(_behavior("a"), _behavior("b")))
        assert len(rule_empty_behaviors(spec)) == 2


class TestRuleMissingModel:
    def test_model_present_returns_empty(self) -> None:
        spec = _spec(model="gpt-4o")
        assert rule_missing_model(spec) == []

    def test_model_absent_raises_bsl006(self) -> None:
        spec = _spec(model=None)
        diags = rule_missing_model(spec)
        assert len(diags) == 1
        assert diags[0].code == "BSL006"
        assert diags[0].severity == DiagnosticSeverity.WARNING


class TestRuleMissingVersion:
    def test_version_present_returns_empty(self) -> None:
        spec = _spec(version="1.0.0")
        assert rule_missing_version(spec) == []

    def test_version_absent_raises_bsl007(self) -> None:
        spec = _spec(version=None)
        diags = rule_missing_version(spec)
        assert len(diags) == 1
        assert diags[0].code == "BSL007"
        assert diags[0].severity == DiagnosticSeverity.WARNING


class TestRuleConflictingConstraints:
    def test_no_conflict_returns_empty(self) -> None:
        spec = _spec(
            behaviors=(
                _behavior(
                    "respond",
                    must=(_constraint("safe"),),
                    must_not=(_constraint("harmful"),),
                ),
            )
        )
        assert rule_conflicting_constraints(spec) == []

    def test_same_expr_in_must_and_must_not_raises_bsl008(self) -> None:
        spec = _spec(
            behaviors=(
                _behavior(
                    "respond",
                    must=(_constraint("flagged"),),
                    must_not=(_constraint("flagged"),),
                ),
            )
        )
        diags = rule_conflicting_constraints(spec)
        assert len(diags) == 1
        assert diags[0].code == "BSL008"
        assert diags[0].severity == DiagnosticSeverity.ERROR
        assert "flagged" in diags[0].message

    def test_conflict_detection_works_with_dot_access(self) -> None:
        dot_expr = DotAccess(parts=("response", "status"), span=_S)
        must_c = Constraint(expression=dot_expr, span=_S)
        must_not_c = Constraint(expression=dot_expr, span=_S)
        spec = _spec(
            behaviors=(
                _behavior("respond", must=(must_c,), must_not=(must_not_c,)),
            )
        )
        diags = rule_conflicting_constraints(spec)
        assert len(diags) == 1
        assert diags[0].code == "BSL008"

    def test_conflict_detection_works_with_string_lit(self) -> None:
        expr = _str_lit("error")
        must_c = Constraint(expression=expr, span=_S)
        must_not_c = Constraint(expression=expr, span=_S)
        spec = _spec(
            behaviors=(_behavior("respond", must=(must_c,), must_not=(must_not_c,)),)
        )
        diags = rule_conflicting_constraints(spec)
        assert len(diags) == 1

    def test_conflict_detection_with_number_lit(self) -> None:
        expr = _num_lit(42.0)
        must_c = Constraint(expression=expr, span=_S)
        must_not_c = Constraint(expression=expr, span=_S)
        spec = _spec(
            behaviors=(_behavior("respond", must=(must_c,), must_not=(must_not_c,)),)
        )
        diags = rule_conflicting_constraints(spec)
        assert len(diags) == 1

    def test_conflict_detection_with_bool_lit(self) -> None:
        expr = _bool_lit(True)
        must_c = Constraint(expression=expr, span=_S)
        must_not_c = Constraint(expression=expr, span=_S)
        spec = _spec(
            behaviors=(_behavior("respond", must=(must_c,), must_not=(must_not_c,)),)
        )
        diags = rule_conflicting_constraints(spec)
        assert len(diags) == 1

    def test_conflict_detection_with_binary_op_expr(self) -> None:
        left = _ident("x")
        right = _num_lit(1.0)
        expr = BinaryOpExpr(op=BinOp.GT, left=left, right=right, span=_S)
        must_c = Constraint(expression=expr, span=_S)
        must_not_c = Constraint(expression=expr, span=_S)
        spec = _spec(
            behaviors=(_behavior("respond", must=(must_c,), must_not=(must_not_c,)),)
        )
        diags = rule_conflicting_constraints(spec)
        assert len(diags) == 1

    def test_conflict_detection_with_contains_expr(self) -> None:
        subject = _ident("response")
        value = _str_lit("error")
        expr = ContainsExpr(subject=subject, value=value, span=_S)
        must_c = Constraint(expression=expr, span=_S)
        must_not_c = Constraint(expression=expr, span=_S)
        spec = _spec(
            behaviors=(_behavior("respond", must=(must_c,), must_not=(must_not_c,)),)
        )
        diags = rule_conflicting_constraints(spec)
        assert len(diags) == 1

    def test_conflict_detection_with_in_list_expr(self) -> None:
        subject = _ident("status")
        items = (_num_lit(200.0), _num_lit(201.0))
        expr = InListExpr(subject=subject, items=items, span=_S)
        must_c = Constraint(expression=expr, span=_S)
        must_not_c = Constraint(expression=expr, span=_S)
        spec = _spec(
            behaviors=(_behavior("respond", must=(must_c,), must_not=(must_not_c,)),)
        )
        diags = rule_conflicting_constraints(spec)
        assert len(diags) == 1

    def test_no_conflict_different_exprs(self) -> None:
        must_c = _constraint("safe")
        must_not_c = _constraint("harmful")
        spec = _spec(
            behaviors=(_behavior("respond", must=(must_c,), must_not=(must_not_c,)),)
        )
        assert rule_conflicting_constraints(spec) == []


class TestRuleUndefinedDegradationTarget:
    def test_valid_degradation_target_returns_empty(self) -> None:
        behavior = _behavior("fallback")
        deg = Degradation(fallback="fallback", condition=_ident("overloaded"), span=_S)
        spec = _spec(behaviors=(behavior,), degradations=(deg,))
        assert rule_undefined_degradation_target(spec) == []

    def test_undefined_degradation_target_raises_bsl009(self) -> None:
        deg = Degradation(fallback="ghost_behavior", condition=_ident("overloaded"), span=_S)
        spec = _spec(degradations=(deg,))
        diags = rule_undefined_degradation_target(spec)
        assert len(diags) == 1
        assert diags[0].code == "BSL009"
        assert diags[0].severity == DiagnosticSeverity.WARNING
        assert "ghost_behavior" in diags[0].message

    def test_no_degradations_returns_empty(self) -> None:
        assert rule_undefined_degradation_target(_spec()) == []


class TestRuleThresholdSanity:
    def test_valid_confidence_percentage_returns_empty(self) -> None:
        conf = _threshold(">=", 95.0, pct=True)
        spec = _spec(behaviors=(_behavior("a", confidence=conf),))
        assert rule_threshold_sanity(spec) == []

    def test_invalid_confidence_percentage_over_100_raises_bsl010(self) -> None:
        conf = _threshold(">=", 110.0, pct=True)
        spec = _spec(behaviors=(_behavior("a", confidence=conf),))
        diags = rule_threshold_sanity(spec)
        assert any(d.code == "BSL010" for d in diags)
        assert all(d.severity == DiagnosticSeverity.ERROR for d in diags)

    def test_invalid_confidence_percentage_negative_raises_bsl010(self) -> None:
        conf = _threshold(">=", -5.0, pct=True)
        spec = _spec(behaviors=(_behavior("a", confidence=conf),))
        diags = rule_threshold_sanity(spec)
        assert any(d.code == "BSL010" for d in diags)

    def test_non_percentage_confidence_skips_range_check(self) -> None:
        conf = _threshold(">=", 0.95, pct=False)
        spec = _spec(behaviors=(_behavior("a", confidence=conf),))
        # non-percentage confidence of 0.95 is fine
        assert rule_threshold_sanity(spec) == []

    def test_negative_latency_raises_bsl010(self) -> None:
        lat = _threshold("<", -100.0, pct=False)
        spec = _spec(behaviors=(_behavior("a", latency=lat),))
        diags = rule_threshold_sanity(spec)
        assert any(d.code == "BSL010" for d in diags)

    def test_valid_latency_returns_empty(self) -> None:
        lat = _threshold("<", 500.0, pct=False)
        spec = _spec(behaviors=(_behavior("a", latency=lat),))
        assert rule_threshold_sanity(spec) == []

    def test_negative_cost_raises_bsl010(self) -> None:
        cost = _threshold("<", -0.01, pct=False)
        spec = _spec(behaviors=(_behavior("a", cost=cost),))
        diags = rule_threshold_sanity(spec)
        assert any(d.code == "BSL010" for d in diags)

    def test_valid_cost_returns_empty(self) -> None:
        cost = _threshold("<", 0.05, pct=False)
        spec = _spec(behaviors=(_behavior("a", cost=cost),))
        assert rule_threshold_sanity(spec) == []

    def test_no_thresholds_returns_empty(self) -> None:
        spec = _spec(behaviors=(_behavior("a"),))
        assert rule_threshold_sanity(spec) == []


class TestDefaultRules:
    def test_default_rules_is_list(self) -> None:
        assert isinstance(DEFAULT_RULES, list)

    def test_default_rules_has_ten_entries(self) -> None:
        assert len(DEFAULT_RULES) == 10

    def test_all_default_rules_are_callable(self) -> None:
        for rule in DEFAULT_RULES:
            assert callable(rule)


# ===========================================================================
# Validator class
# ===========================================================================


class TestValidator:
    def test_default_rule_count(self) -> None:
        v = Validator()
        assert v.rule_count == len(DEFAULT_RULES)

    def test_custom_rules_override_defaults(self) -> None:
        v = Validator(rules=[])
        assert v.rule_count == 0

    def test_add_rule_increments_count(self) -> None:
        v = Validator(rules=[])
        v.add_rule(rule_missing_model)
        assert v.rule_count == 1

    def test_validate_clean_spec_returns_empty(self) -> None:
        beh = _behavior("respond", must=(_constraint("safe"),))
        spec = _spec(behaviors=(beh,))
        v = Validator()
        diags = v.validate(spec)
        # Expect only warnings (missing owner maybe) but no rule errors for clean spec
        errors = [d for d in diags if d.is_error]
        assert errors == []

    def test_validate_returns_sorted_by_line_col(self) -> None:
        # Duplicate behaviors: both have Span.unknown (line 0, col 0)
        spec = _spec(
            behaviors=(_behavior("a"), _behavior("a"), _behavior("b"), _behavior("b"))
        )
        v = Validator()
        diags = v.validate(spec)
        lines_cols = [(d.span.line, d.span.col) for d in diags]
        assert lines_cols == sorted(lines_cols)

    def test_strict_mode_promotes_warnings_to_errors(self) -> None:
        # A spec missing model and version will produce BSL006 and BSL007 (warnings)
        spec = _spec(version=None, model=None)
        v = Validator(strict=True)
        diags = v.validate(spec)
        warning_codes = {"BSL006", "BSL007"}
        promoted = [d for d in diags if d.code in warning_codes]
        assert all(d.severity == DiagnosticSeverity.ERROR for d in promoted)

    def test_non_strict_mode_preserves_warning_severity(self) -> None:
        spec = _spec(version=None, model=None)
        v = Validator(strict=False)
        diags = v.validate(spec)
        warning_codes = {"BSL006", "BSL007"}
        warnings = [d for d in diags if d.code in warning_codes]
        assert all(d.severity == DiagnosticSeverity.WARNING for d in warnings)

    def test_broken_rule_produces_bsl999_internal_error(self) -> None:
        def bad_rule(spec: AgentSpec) -> list[Diagnostic]:
            raise RuntimeError("simulated rule crash")

        v = Validator(rules=[bad_rule])
        spec = _spec()
        diags = v.validate(spec)
        assert len(diags) == 1
        assert diags[0].code == "BSL999"
        assert diags[0].severity == DiagnosticSeverity.ERROR
        assert "bad_rule" in diags[0].message

    def test_multiple_rules_aggregate_results(self) -> None:
        # Two rules each returning one diagnostic
        def rule_a(spec: AgentSpec) -> list[Diagnostic]:
            return [Diagnostic(
                severity=DiagnosticSeverity.WARNING,
                code="TEST001",
                message="from rule_a",
                span=spec.span,
            )]

        def rule_b(spec: AgentSpec) -> list[Diagnostic]:
            return [Diagnostic(
                severity=DiagnosticSeverity.ERROR,
                code="TEST002",
                message="from rule_b",
                span=spec.span,
            )]

        v = Validator(rules=[rule_a, rule_b])
        diags = v.validate(_spec())
        codes = {d.code for d in diags}
        assert "TEST001" in codes
        assert "TEST002" in codes


class TestValidateConvenienceFunction:
    def test_returns_list(self) -> None:
        spec = _spec()
        result = validate(spec)
        assert isinstance(result, list)

    def test_strict_kwarg_is_forwarded(self) -> None:
        # With strict=True, BSL007/BSL006 warnings become errors
        spec = _spec(version=None, model=None)
        strict_diags = validate(spec, strict=True)
        normal_diags = validate(spec, strict=False)
        strict_errors = [d for d in strict_diags if d.is_error and d.code in {"BSL006", "BSL007"}]
        normal_errors = [d for d in normal_diags if d.is_error and d.code in {"BSL006", "BSL007"}]
        assert len(strict_errors) > len(normal_errors)
