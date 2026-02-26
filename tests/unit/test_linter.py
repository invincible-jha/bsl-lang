"""Unit tests for the BSL linter: linter.py, naming.py, completeness.py,
and consistency.py — all linter rules and the BslLinter class.
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
    DotAccess,
    EscalationClause,
    Identifier,
    Invariant,
    NumberLit,
    Receives,
    Severity,
    ShouldConstraint,
    Span,
    StringLit,
    ThresholdClause,
)
from bsl.linter.linter import BslLinter, lint
from bsl.linter.rules import ALL_LINT_RULES, COMPLETENESS_RULES, CONSISTENCY_RULES, NAMING_RULES
from bsl.linter.rules.completeness import (
    COMPLETENESS_RULES,
    rule_agent_has_owner,
    rule_audit_coverage,
    rule_behavior_has_confidence,
    rule_behavior_has_latency,
    rule_has_behaviors,
    rule_has_invariants,
    rule_invariant_has_content,
)
from bsl.linter.rules.consistency import (
    CONSISTENCY_RULES,
    rule_consistent_escalation,
    rule_consistent_should_percentages,
    rule_no_deprecated_models,
    rule_no_duplicate_must_across_behaviors,
    rule_unique_when_clauses,
)
from bsl.linter.rules.naming import (
    NAMING_RULES,
    rule_agent_name_pascal_case,
    rule_behavior_name_length,
    rule_behavior_name_not_generic,
    rule_behavior_name_snake_case,
    rule_invariant_name_snake_case,
)
from bsl.validator.diagnostics import Diagnostic, DiagnosticSeverity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_S = Span.unknown()


def _ident(name: str) -> Identifier:
    return Identifier(name=name, span=_S)


def _constraint(name: str) -> Constraint:
    return Constraint(expression=_ident(name), span=_S)


def _should(name: str, pct: float | None = None) -> ShouldConstraint:
    return ShouldConstraint(expression=_ident(name), percentage=pct, span=_S)


def _threshold(op: str, value: float, pct: bool = False) -> ThresholdClause:
    return ThresholdClause(operator=op, value=value, is_percentage=pct, span=_S)


def _escalation(cond_name: str) -> EscalationClause:
    return EscalationClause(condition=_ident(cond_name), span=_S)


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
        cost=None,
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
    version: str | None = "1.0.0",
    model: str | None = "gpt-4o",
    owner: str | None = "team@example.com",
    behaviors: tuple[Behavior, ...] = (),
    invariants: tuple[Invariant, ...] = (),
) -> AgentSpec:
    return AgentSpec(
        name=name,
        version=version,
        model=model,
        owner=owner,
        behaviors=behaviors,
        invariants=invariants,
        degradations=(),
        compositions=(),
        span=_S,
    )


# ===========================================================================
# Naming rules
# ===========================================================================


class TestRuleAgentNamePascalCase:
    def test_pascal_case_returns_empty(self) -> None:
        spec = _spec(name="CustomerServiceAgent")
        assert rule_agent_name_pascal_case(spec) == []

    def test_single_word_capital_returns_empty(self) -> None:
        spec = _spec(name="Agent")
        assert rule_agent_name_pascal_case(spec) == []

    def test_snake_case_name_raises_lint_n001(self) -> None:
        spec = _spec(name="customer_service_agent")
        diags = rule_agent_name_pascal_case(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-N001"
        assert diags[0].severity == DiagnosticSeverity.WARNING

    def test_lowercase_name_raises_lint_n001(self) -> None:
        spec = _spec(name="myagent")
        diags = rule_agent_name_pascal_case(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-N001"

    def test_suggestion_is_present(self) -> None:
        spec = _spec(name="bad_name")
        diag = rule_agent_name_pascal_case(spec)[0]
        assert diag.suggestion is not None

    def test_rule_field_is_naming(self) -> None:
        spec = _spec(name="bad_name")
        diag = rule_agent_name_pascal_case(spec)[0]
        assert diag.rule == "naming"


class TestRuleBehaviorNameSnakeCase:
    def test_snake_case_returns_empty(self) -> None:
        spec = _spec(behaviors=(_behavior("respond_to_user"),))
        assert rule_behavior_name_snake_case(spec) == []

    def test_single_lowercase_word_returns_empty(self) -> None:
        spec = _spec(behaviors=(_behavior("respond"),))
        assert rule_behavior_name_snake_case(spec) == []

    def test_pascal_case_behavior_raises_lint_n002(self) -> None:
        spec = _spec(behaviors=(_behavior("RespondToUser"),))
        diags = rule_behavior_name_snake_case(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-N002"
        assert diags[0].severity == DiagnosticSeverity.WARNING

    def test_camel_case_behavior_raises_lint_n002(self) -> None:
        spec = _spec(behaviors=(_behavior("respondToUser"),))
        diags = rule_behavior_name_snake_case(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-N002"

    def test_hyphenated_behavior_raises_lint_n002(self) -> None:
        spec = _spec(behaviors=(_behavior("respond-to-user"),))
        diags = rule_behavior_name_snake_case(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-N002"

    def test_multiple_bad_names_produce_multiple_diags(self) -> None:
        spec = _spec(behaviors=(_behavior("BadName"), _behavior("AnotherBad")))
        diags = rule_behavior_name_snake_case(spec)
        assert len(diags) == 2

    def test_no_behaviors_returns_empty(self) -> None:
        assert rule_behavior_name_snake_case(_spec()) == []


class TestRuleInvariantNameSnakeCase:
    def test_snake_case_returns_empty(self) -> None:
        spec = _spec(invariants=(_invariant("safety_check"),))
        assert rule_invariant_name_snake_case(spec) == []

    def test_pascal_case_invariant_raises_lint_n003(self) -> None:
        spec = _spec(invariants=(_invariant("SafetyCheck"),))
        diags = rule_invariant_name_snake_case(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-N003"
        assert diags[0].severity == DiagnosticSeverity.WARNING

    def test_no_invariants_returns_empty(self) -> None:
        assert rule_invariant_name_snake_case(_spec()) == []


class TestRuleBehaviorNameLength:
    def test_name_3_chars_returns_empty(self) -> None:
        spec = _spec(behaviors=(_behavior("run"),))
        # "run" is 3 chars, which is exactly the threshold — but it's in _GENERIC_NAMES
        # the length rule checks < 3, so "ab" (2 chars) triggers it
        diags = rule_behavior_name_length(spec)
        assert diags == []

    def test_name_2_chars_raises_lint_n004(self) -> None:
        spec = _spec(behaviors=(_behavior("ab"),))
        diags = rule_behavior_name_length(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-N004"
        assert diags[0].severity == DiagnosticSeverity.HINT

    def test_name_1_char_raises_lint_n004(self) -> None:
        spec = _spec(behaviors=(_behavior("a"),))
        diags = rule_behavior_name_length(spec)
        assert len(diags) == 1

    def test_long_name_returns_empty(self) -> None:
        spec = _spec(behaviors=(_behavior("respond_to_complex_user_query"),))
        assert rule_behavior_name_length(spec) == []


class TestRuleBehaviorNameNotGeneric:
    @pytest.mark.parametrize("generic_name", [
        "do", "run", "execute", "process", "handle", "action", "task"
    ])
    def test_generic_names_raise_lint_n005(self, generic_name: str) -> None:
        spec = _spec(behaviors=(_behavior(generic_name),))
        diags = rule_behavior_name_not_generic(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-N005"
        assert diags[0].severity == DiagnosticSeverity.HINT

    def test_descriptive_name_returns_empty(self) -> None:
        spec = _spec(behaviors=(_behavior("respond_to_user_query"),))
        assert rule_behavior_name_not_generic(spec) == []

    def test_no_behaviors_returns_empty(self) -> None:
        assert rule_behavior_name_not_generic(_spec()) == []


class TestNamingRulesList:
    def test_naming_rules_has_five_entries(self) -> None:
        assert len(NAMING_RULES) == 5

    def test_all_naming_rules_callable(self) -> None:
        for rule in NAMING_RULES:
            assert callable(rule)


# ===========================================================================
# Completeness rules
# ===========================================================================


class TestRuleHasBehaviors:
    def test_spec_with_behaviors_returns_empty(self) -> None:
        spec = _spec(behaviors=(_behavior("respond"),))
        assert rule_has_behaviors(spec) == []

    def test_spec_without_behaviors_raises_lint_c001(self) -> None:
        spec = _spec()
        diags = rule_has_behaviors(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-C001"
        assert diags[0].severity == DiagnosticSeverity.WARNING


class TestRuleHasInvariants:
    def test_spec_with_invariants_returns_empty(self) -> None:
        spec = _spec(invariants=(_invariant("safety"),))
        assert rule_has_invariants(spec) == []

    def test_spec_without_invariants_raises_lint_c002(self) -> None:
        spec = _spec()
        diags = rule_has_invariants(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-C002"
        assert diags[0].severity == DiagnosticSeverity.HINT


class TestRuleBehaviorHasConfidence:
    def test_behavior_with_confidence_returns_empty(self) -> None:
        conf = _threshold(">=", 0.9)
        spec = _spec(behaviors=(_behavior("respond", confidence=conf),))
        assert rule_behavior_has_confidence(spec) == []

    def test_behavior_without_confidence_raises_lint_c003(self) -> None:
        spec = _spec(behaviors=(_behavior("respond"),))
        diags = rule_behavior_has_confidence(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-C003"
        assert diags[0].severity == DiagnosticSeverity.HINT

    def test_multiple_behaviors_without_confidence_produce_multiple_diags(self) -> None:
        spec = _spec(behaviors=(_behavior("a"), _behavior("b")))
        assert len(rule_behavior_has_confidence(spec)) == 2


class TestRuleBehaviorHasLatency:
    def test_behavior_with_latency_returns_empty(self) -> None:
        lat = _threshold("<", 500.0)
        spec = _spec(behaviors=(_behavior("respond", latency=lat),))
        assert rule_behavior_has_latency(spec) == []

    def test_behavior_without_latency_raises_lint_c004(self) -> None:
        spec = _spec(behaviors=(_behavior("respond"),))
        diags = rule_behavior_has_latency(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-C004"
        assert diags[0].severity == DiagnosticSeverity.HINT


class TestRuleAgentHasOwner:
    def test_spec_with_owner_returns_empty(self) -> None:
        spec = _spec(owner="team@example.com")
        assert rule_agent_has_owner(spec) == []

    def test_spec_without_owner_raises_lint_c005(self) -> None:
        spec = _spec(owner=None)
        diags = rule_agent_has_owner(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-C005"
        assert diags[0].severity == DiagnosticSeverity.WARNING


class TestRuleInvariantHasContent:
    def test_invariant_with_constraint_returns_empty(self) -> None:
        inv = _invariant("safety", constraints=(_constraint("safe"),))
        spec = _spec(invariants=(inv,))
        assert rule_invariant_has_content(spec) == []

    def test_invariant_with_prohibition_returns_empty(self) -> None:
        inv = _invariant("safety", prohibitions=(_constraint("harmful"),))
        spec = _spec(invariants=(inv,))
        assert rule_invariant_has_content(spec) == []

    def test_empty_invariant_raises_lint_c006(self) -> None:
        inv = _invariant("empty_inv")
        spec = _spec(invariants=(inv,))
        diags = rule_invariant_has_content(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-C006"
        assert diags[0].severity == DiagnosticSeverity.WARNING


class TestRuleAuditCoverage:
    def test_behavior_with_basic_audit_returns_empty(self) -> None:
        spec = _spec(behaviors=(_behavior("respond", audit=AuditLevel.BASIC),))
        assert rule_audit_coverage(spec) == []

    def test_behavior_with_full_trace_audit_returns_empty(self) -> None:
        spec = _spec(behaviors=(_behavior("respond", audit=AuditLevel.FULL_TRACE),))
        assert rule_audit_coverage(spec) == []

    def test_all_behaviors_with_no_audit_raises_lint_c008(self) -> None:
        spec = _spec(behaviors=(_behavior("respond", audit=AuditLevel.NONE),))
        diags = rule_audit_coverage(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-C008"
        assert diags[0].severity == DiagnosticSeverity.HINT

    def test_mixed_audit_levels_returns_empty(self) -> None:
        spec = _spec(
            behaviors=(
                _behavior("a", audit=AuditLevel.NONE),
                _behavior("b", audit=AuditLevel.BASIC),
            )
        )
        assert rule_audit_coverage(spec) == []

    def test_no_behaviors_returns_empty(self) -> None:
        assert rule_audit_coverage(_spec()) == []


class TestCompletenessRulesList:
    def test_completeness_rules_count(self) -> None:
        assert len(COMPLETENESS_RULES) == 7

    def test_all_completeness_rules_callable(self) -> None:
        for rule in COMPLETENESS_RULES:
            assert callable(rule)


# ===========================================================================
# Consistency rules
# ===========================================================================


class TestRuleConsistentShouldPercentages:
    def test_same_percentages_returns_empty(self) -> None:
        b1 = _behavior("a", should=(_should("polite", 80.0),))
        b2 = _behavior("b", should=(_should("polite", 80.0),))
        spec = _spec(behaviors=(b1, b2))
        assert rule_consistent_should_percentages(spec) == []

    def test_different_percentages_same_expr_raises_lint_x001(self) -> None:
        b1 = _behavior("a", should=(_should("polite", 80.0),))
        b2 = _behavior("b", should=(_should("polite", 60.0),))
        spec = _spec(behaviors=(b1, b2))
        diags = rule_consistent_should_percentages(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-X001"
        assert diags[0].severity == DiagnosticSeverity.HINT

    def test_only_one_behavior_with_pct_returns_empty(self) -> None:
        b = _behavior("a", should=(_should("polite", 80.0),))
        spec = _spec(behaviors=(b,))
        assert rule_consistent_should_percentages(spec) == []

    def test_no_percentages_returns_empty(self) -> None:
        b1 = _behavior("a", should=(_should("polite", None),))
        b2 = _behavior("b", should=(_should("polite", None),))
        spec = _spec(behaviors=(b1, b2))
        assert rule_consistent_should_percentages(spec) == []


class TestRuleConsistentEscalation:
    def test_all_behaviors_have_escalation_returns_empty(self) -> None:
        b1 = _behavior("a", escalation=_escalation("angry"))
        b2 = _behavior("b", escalation=_escalation("confused"))
        spec = _spec(behaviors=(b1, b2))
        assert rule_consistent_escalation(spec) == []

    def test_no_behaviors_with_escalation_returns_empty(self) -> None:
        b1 = _behavior("a")
        b2 = _behavior("b")
        spec = _spec(behaviors=(b1, b2))
        assert rule_consistent_escalation(spec) == []

    def test_mixed_escalation_raises_lint_x002(self) -> None:
        b1 = _behavior("a", escalation=_escalation("angry"))
        b2 = _behavior("b")
        spec = _spec(behaviors=(b1, b2))
        diags = rule_consistent_escalation(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-X002"
        assert diags[0].severity == DiagnosticSeverity.HINT

    def test_single_behavior_returns_empty(self) -> None:
        b = _behavior("a", escalation=_escalation("angry"))
        spec = _spec(behaviors=(b,))
        assert rule_consistent_escalation(spec) == []

    def test_more_than_3_without_escalation_truncates_message(self) -> None:
        behaviors_with = (_behavior("a", escalation=_escalation("cond")),)
        behaviors_without = tuple(_behavior(f"b{i}") for i in range(5))
        spec = _spec(behaviors=behaviors_with + behaviors_without)
        diags = rule_consistent_escalation(spec)
        assert len(diags) == 1
        assert "+2 more" in diags[0].message


class TestRuleNoDuplicateMustAcrossBehaviors:
    def test_no_shared_musts_returns_empty(self) -> None:
        b1 = _behavior("a", must=(_constraint("safe"),))
        b2 = _behavior("b", must=(_constraint("accurate"),))
        spec = _spec(behaviors=(b1, b2))
        assert rule_no_duplicate_must_across_behaviors(spec) == []

    def test_shared_must_in_3_plus_behaviors_raises_lint_x003(self) -> None:
        c = _constraint("safe")
        b1 = _behavior("a", must=(c,))
        b2 = _behavior("b", must=(c,))
        b3 = _behavior("c", must=(c,))
        spec = _spec(behaviors=(b1, b2, b3))
        diags = rule_no_duplicate_must_across_behaviors(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-X003"
        assert diags[0].severity == DiagnosticSeverity.HINT

    def test_shared_must_in_2_behaviors_returns_empty(self) -> None:
        c = _constraint("safe")
        b1 = _behavior("a", must=(c,))
        b2 = _behavior("b", must=(c,))
        spec = _spec(behaviors=(b1, b2))
        assert rule_no_duplicate_must_across_behaviors(spec) == []


class TestRuleUniqueWhenClauses:
    def test_different_when_clauses_returns_empty(self) -> None:
        b1 = _behavior("a", when_clause=_ident("context_a"))
        b2 = _behavior("b", when_clause=_ident("context_b"))
        spec = _spec(behaviors=(b1, b2))
        assert rule_unique_when_clauses(spec) == []

    def test_same_when_clause_raises_lint_x004(self) -> None:
        cond = _ident("online")
        b1 = _behavior("a", when_clause=cond)
        b2 = _behavior("b", when_clause=cond)
        spec = _spec(behaviors=(b1, b2))
        diags = rule_unique_when_clauses(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-X004"
        assert diags[0].severity == DiagnosticSeverity.WARNING

    def test_no_when_clauses_returns_empty(self) -> None:
        b1 = _behavior("a")
        b2 = _behavior("b")
        spec = _spec(behaviors=(b1, b2))
        assert rule_unique_when_clauses(spec) == []


class TestRuleNoDeprecatedModels:
    @pytest.mark.parametrize("deprecated_model", [
        "gpt-3", "gpt-3.5-turbo", "text-davinci-003", "claude-1", "claude-2"
    ])
    def test_deprecated_model_raises_lint_x005(self, deprecated_model: str) -> None:
        spec = _spec(model=deprecated_model)
        diags = rule_no_deprecated_models(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-X005"
        assert diags[0].severity == DiagnosticSeverity.WARNING

    def test_current_model_returns_empty(self) -> None:
        spec = _spec(model="gpt-4o")
        assert rule_no_deprecated_models(spec) == []

    def test_no_model_returns_empty(self) -> None:
        spec = _spec(model=None)
        assert rule_no_deprecated_models(spec) == []

    def test_case_insensitive_detection(self) -> None:
        spec = _spec(model="GPT-3")
        diags = rule_no_deprecated_models(spec)
        assert len(diags) == 1


class TestConsistencyRulesList:
    def test_consistency_rules_count(self) -> None:
        assert len(CONSISTENCY_RULES) == 5

    def test_all_consistency_rules_callable(self) -> None:
        for rule in CONSISTENCY_RULES:
            assert callable(rule)


# ===========================================================================
# BslLinter class
# ===========================================================================


class TestBslLinter:
    def test_default_rule_count_equals_all_rules(self) -> None:
        linter = BslLinter()
        assert linter.rule_count == len(ALL_LINT_RULES)

    def test_custom_rules_override_defaults(self) -> None:
        linter = BslLinter(rules=[])
        assert linter.rule_count == 0

    def test_add_rule_increments_count(self) -> None:
        linter = BslLinter(rules=[])
        linter.add_rule(rule_has_behaviors)
        assert linter.rule_count == 1

    def test_lint_returns_sorted_by_line_col(self) -> None:
        spec = _spec(
            name="bad_name",  # triggers LINT-N001 (line 0)
            behaviors=(_behavior("BadBehavior"),),  # triggers LINT-N002
        )
        linter = BslLinter(rules=[rule_agent_name_pascal_case, rule_behavior_name_snake_case])
        diags = linter.lint(spec)
        lines_cols = [(d.span.line, d.span.col) for d in diags]
        assert lines_cols == sorted(lines_cols)

    def test_include_hints_true_keeps_hints(self) -> None:
        spec = _spec()  # triggers has_invariants HINT and has_behaviors HINT/WARNING
        linter = BslLinter(
            rules=[rule_has_invariants, rule_behavior_has_confidence],
            include_hints=True,
        )
        diags = linter.lint(spec)
        hints = [d for d in diags if d.severity == DiagnosticSeverity.HINT]
        assert len(hints) > 0

    def test_include_hints_false_removes_hints(self) -> None:
        spec = _spec(behaviors=(_behavior("respond"),))
        linter = BslLinter(
            rules=[rule_behavior_has_confidence],
            include_hints=False,
        )
        diags = linter.lint(spec)
        assert all(d.severity != DiagnosticSeverity.HINT for d in diags)

    def test_broken_rule_produces_lint_999_error(self) -> None:
        def bad_rule(spec: AgentSpec) -> list[Diagnostic]:
            raise ValueError("rule explosion")

        linter = BslLinter(rules=[bad_rule])
        spec = _spec()
        diags = linter.lint(spec)
        assert len(diags) == 1
        assert diags[0].code == "LINT-999"
        assert diags[0].severity == DiagnosticSeverity.ERROR

    def test_multiple_rules_aggregate_results(self) -> None:
        spec = _spec(name="bad_agent")  # LINT-N001
        linter = BslLinter(rules=[rule_agent_name_pascal_case, rule_has_behaviors])
        diags = linter.lint(spec)
        codes = {d.code for d in diags}
        assert "LINT-N001" in codes
        assert "LINT-C001" in codes


class TestLintConvenienceFunction:
    def test_returns_list(self) -> None:
        spec = _spec()
        result = lint(spec)
        assert isinstance(result, list)

    def test_include_hints_false_filters_hints(self) -> None:
        spec = _spec(behaviors=(_behavior("respond"),))
        all_diags = lint(spec, include_hints=True)
        no_hints = lint(spec, include_hints=False)
        hint_count = sum(1 for d in all_diags if d.severity == DiagnosticSeverity.HINT)
        assert len(no_hints) <= len(all_diags) - hint_count

    def test_all_lint_rules_list_contains_all_groups(self) -> None:
        all_names = {r.__name__ for r in ALL_LINT_RULES}
        naming_names = {r.__name__ for r in NAMING_RULES}
        completeness_names = {r.__name__ for r in COMPLETENESS_RULES}
        consistency_names = {r.__name__ for r in CONSISTENCY_RULES}
        assert naming_names.issubset(all_names)
        assert completeness_names.issubset(all_names)
        assert consistency_names.issubset(all_names)
