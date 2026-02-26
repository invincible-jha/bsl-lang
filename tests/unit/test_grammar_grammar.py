"""Unit tests for bsl.grammar.grammar — EBNF constants and ordering lists."""
from __future__ import annotations

import pytest

from bsl.grammar.grammar import (
    AGENT_METADATA_ORDER,
    BEHAVIOR_CLAUSE_ORDER,
    FULL_GRAMMAR,
    GRAMMAR_BEHAVIOR,
    GRAMMAR_COMPOSITION,
    GRAMMAR_DEGRADATION,
    GRAMMAR_EXPRESSION,
    GRAMMAR_INVARIANT,
    GRAMMAR_METADATA,
    GRAMMAR_ROOT,
    GRAMMAR_THRESHOLD,
    INVARIANT_CLAUSE_ORDER,
)


class TestGrammarConstants:
    def test_grammar_root_contains_agent_spec(self) -> None:
        assert "agent_spec" in GRAMMAR_ROOT

    def test_grammar_root_contains_bsl_file(self) -> None:
        assert "bsl_file" in GRAMMAR_ROOT

    def test_grammar_metadata_contains_version_decl(self) -> None:
        assert "version_decl" in GRAMMAR_METADATA

    def test_grammar_metadata_contains_model_decl(self) -> None:
        assert "model_decl" in GRAMMAR_METADATA

    def test_grammar_metadata_contains_owner_decl(self) -> None:
        assert "owner_decl" in GRAMMAR_METADATA

    def test_grammar_behavior_contains_must_clause(self) -> None:
        assert "must_clause" in GRAMMAR_BEHAVIOR

    def test_grammar_behavior_contains_must_not_clause(self) -> None:
        assert "must_not_clause" in GRAMMAR_BEHAVIOR

    def test_grammar_behavior_contains_should_clause(self) -> None:
        assert "should_clause" in GRAMMAR_BEHAVIOR

    def test_grammar_behavior_contains_when_clause(self) -> None:
        assert "when_clause" in GRAMMAR_BEHAVIOR

    def test_grammar_threshold_contains_comparison_op(self) -> None:
        assert "comparison_op" in GRAMMAR_THRESHOLD

    def test_grammar_invariant_contains_applies_to(self) -> None:
        assert "applies_to_clause" in GRAMMAR_INVARIANT

    def test_grammar_invariant_contains_severity(self) -> None:
        assert "severity_clause" in GRAMMAR_INVARIANT

    def test_grammar_degradation_contains_degrades_to(self) -> None:
        assert "degrades_to" in GRAMMAR_DEGRADATION

    def test_grammar_composition_contains_receives(self) -> None:
        assert "receives_decl" in GRAMMAR_COMPOSITION

    def test_grammar_composition_contains_delegates(self) -> None:
        assert "delegates_decl" in GRAMMAR_COMPOSITION

    def test_grammar_expression_contains_or_expr(self) -> None:
        assert "or_expr" in GRAMMAR_EXPRESSION

    def test_grammar_expression_contains_and_expr(self) -> None:
        assert "and_expr" in GRAMMAR_EXPRESSION

    def test_grammar_expression_contains_function_call(self) -> None:
        assert "function_call" in GRAMMAR_EXPRESSION

    def test_full_grammar_is_non_empty_string(self) -> None:
        assert isinstance(FULL_GRAMMAR, str)
        assert len(FULL_GRAMMAR) > 0

    def test_full_grammar_contains_all_sections(self) -> None:
        for section in ("agent_spec", "behavior_decl", "invariant_decl", "expression"):
            assert section in FULL_GRAMMAR


class TestClauseOrdering:
    def test_behavior_clause_order_is_list(self) -> None:
        assert isinstance(BEHAVIOR_CLAUSE_ORDER, list)

    def test_behavior_clause_order_contains_when(self) -> None:
        assert "when" in BEHAVIOR_CLAUSE_ORDER

    def test_behavior_clause_order_contains_must(self) -> None:
        assert "must" in BEHAVIOR_CLAUSE_ORDER

    def test_behavior_clause_order_contains_must_not(self) -> None:
        assert "must_not" in BEHAVIOR_CLAUSE_ORDER

    def test_behavior_clause_order_contains_should(self) -> None:
        assert "should" in BEHAVIOR_CLAUSE_ORDER

    def test_behavior_clause_order_contains_may(self) -> None:
        assert "may" in BEHAVIOR_CLAUSE_ORDER

    def test_when_comes_before_must_in_behavior_order(self) -> None:
        assert BEHAVIOR_CLAUSE_ORDER.index("when") < BEHAVIOR_CLAUSE_ORDER.index("must")

    def test_must_comes_before_should_in_behavior_order(self) -> None:
        assert BEHAVIOR_CLAUSE_ORDER.index("must") < BEHAVIOR_CLAUSE_ORDER.index("should")

    def test_invariant_clause_order_is_list(self) -> None:
        assert isinstance(INVARIANT_CLAUSE_ORDER, list)

    def test_invariant_clause_order_contains_applies_to(self) -> None:
        assert "applies_to" in INVARIANT_CLAUSE_ORDER

    def test_invariant_clause_order_contains_severity(self) -> None:
        assert "severity" in INVARIANT_CLAUSE_ORDER

    def test_applies_to_before_severity_in_invariant_order(self) -> None:
        assert (
            INVARIANT_CLAUSE_ORDER.index("applies_to")
            < INVARIANT_CLAUSE_ORDER.index("severity")
        )

    def test_agent_metadata_order_contains_version(self) -> None:
        assert "version" in AGENT_METADATA_ORDER

    def test_agent_metadata_order_contains_model(self) -> None:
        assert "model" in AGENT_METADATA_ORDER

    def test_agent_metadata_order_contains_owner(self) -> None:
        assert "owner" in AGENT_METADATA_ORDER

    def test_version_first_in_agent_metadata_order(self) -> None:
        assert AGENT_METADATA_ORDER[0] == "version"
