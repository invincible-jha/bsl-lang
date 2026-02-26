"""Unit tests for bsl.parser — recursive-descent parser producing AgentSpec AST."""
from __future__ import annotations

import pytest

from bsl.ast.nodes import (
    AfterExpr,
    AgentSpec,
    AppliesTo,
    AuditLevel,
    BeforeExpr,
    BinOp,
    BinaryOpExpr,
    BoolLit,
    ContainsExpr,
    Delegates,
    DotAccess,
    FunctionCall,
    Identifier,
    InListExpr,
    Invariant,
    NumberLit,
    Receives,
    Severity,
    StringLit,
    UnaryOpExpr,
    UnaryOpKind,
)
from bsl.parser.errors import ParseErrorCollection, RecoveryStrategy
from bsl.parser.parser import Parser, parse
from bsl.lexer.lexer import tokenize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_source(source: str) -> AgentSpec:
    """Parse a BSL source string and return the AgentSpec."""
    return parse(source)


MINIMAL_AGENT = 'agent MinimalAgent { }'

FULL_AGENT = '''
agent FullAgent {
  version: "1.0.0"
  model: "gpt-4o"
  owner: "team-ai"

  behavior greet {
    when: user_message == "hello"
    confidence: >= 95%
    latency: < 500
    cost: <= 0.01
    audit: basic
    escalate_to_human when: confidence < 0.5
    must: response contains "Hello"
    must_not: response contains "Error"
    should: response.length < 200 80% of cases
    may: include_emoji
  }

  invariant safety_rule {
    applies_to: all_behaviors
    severity: critical
    must: not harmful_content
    must_not: pii_leak
  }

  degrades_to FallbackAgent when: error_rate > 0.1

  receives from InputAgent
  delegates_to OutputAgent
}
'''


# ---------------------------------------------------------------------------
# Minimal agent parsing
# ---------------------------------------------------------------------------


class TestMinimalAgentParsing:
    def test_parse_empty_agent_succeeds(self) -> None:
        spec = parse_source(MINIMAL_AGENT)
        assert spec.name == "MinimalAgent"

    def test_empty_agent_has_no_behaviors(self) -> None:
        spec = parse_source(MINIMAL_AGENT)
        assert spec.behaviors == ()

    def test_empty_agent_has_no_invariants(self) -> None:
        spec = parse_source(MINIMAL_AGENT)
        assert spec.invariants == ()

    def test_empty_agent_version_is_none(self) -> None:
        spec = parse_source(MINIMAL_AGENT)
        assert spec.version is None

    def test_empty_agent_model_is_none(self) -> None:
        spec = parse_source(MINIMAL_AGENT)
        assert spec.model is None


# ---------------------------------------------------------------------------
# Metadata parsing
# ---------------------------------------------------------------------------


class TestMetadataParsing:
    def test_version_parsed_correctly(self) -> None:
        spec = parse_source(FULL_AGENT)
        assert spec.version == "1.0.0"

    def test_model_parsed_correctly(self) -> None:
        spec = parse_source(FULL_AGENT)
        assert spec.model == "gpt-4o"

    def test_owner_parsed_correctly(self) -> None:
        spec = parse_source(FULL_AGENT)
        assert spec.owner == "team-ai"

    def test_metadata_only_agent(self) -> None:
        src = 'agent MdAgent { version: "2.0" model: "claude-3" owner: "alice" }'
        spec = parse_source(src)
        assert spec.version == "2.0"
        assert spec.model == "claude-3"
        assert spec.owner == "alice"


# ---------------------------------------------------------------------------
# Behavior parsing
# ---------------------------------------------------------------------------


class TestBehaviorParsing:
    def test_behavior_name_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        assert len(spec.behaviors) == 1
        assert spec.behaviors[0].name == "greet"

    def test_when_clause_parsed_as_binary_op(self) -> None:
        spec = parse_source(FULL_AGENT)
        b = spec.behaviors[0]
        assert b.when_clause is not None
        assert isinstance(b.when_clause, BinaryOpExpr)
        assert b.when_clause.op is BinOp.EQ

    def test_must_constraint_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        b = spec.behaviors[0]
        assert len(b.must_constraints) == 1
        assert isinstance(b.must_constraints[0].expression, ContainsExpr)

    def test_must_not_constraint_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        b = spec.behaviors[0]
        assert len(b.must_not_constraints) == 1

    def test_should_constraint_with_percentage_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        b = spec.behaviors[0]
        assert len(b.should_constraints) == 1
        assert b.should_constraints[0].percentage == 80.0

    def test_confidence_threshold_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        b = spec.behaviors[0]
        assert b.confidence is not None
        assert b.confidence.operator == ">="
        assert b.confidence.value == 95.0
        assert b.confidence.is_percentage is True

    def test_latency_threshold_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        b = spec.behaviors[0]
        assert b.latency is not None
        assert b.latency.operator == "<"
        assert b.latency.value == 500.0

    def test_cost_threshold_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        b = spec.behaviors[0]
        assert b.cost is not None
        assert b.cost.operator == "<="
        assert b.cost.value == pytest.approx(0.01)

    def test_audit_level_basic_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        b = spec.behaviors[0]
        assert b.audit is AuditLevel.BASIC

    def test_audit_level_full_trace_parsed(self) -> None:
        src = 'agent A { behavior b { audit: full_trace must: x } }'
        spec = parse_source(src)
        assert spec.behaviors[0].audit is AuditLevel.FULL_TRACE

    def test_audit_level_none_is_default(self) -> None:
        src = 'agent A { behavior b { must: x } }'
        spec = parse_source(src)
        assert spec.behaviors[0].audit is AuditLevel.NONE

    def test_escalation_clause_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        b = spec.behaviors[0]
        assert b.escalation is not None

    def test_may_constraint_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        b = spec.behaviors[0]
        assert len(b.may_constraints) == 1

    def test_multiple_behaviors_parsed(self) -> None:
        src = '''agent A {
            behavior one { must: x }
            behavior two { must: y }
        }'''
        spec = parse_source(src)
        assert len(spec.behaviors) == 2
        assert spec.behaviors[0].name == "one"
        assert spec.behaviors[1].name == "two"


# ---------------------------------------------------------------------------
# Invariant parsing
# ---------------------------------------------------------------------------


class TestInvariantParsing:
    def test_invariant_name_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        assert len(spec.invariants) == 1
        assert spec.invariants[0].name == "safety_rule"

    def test_applies_to_all_behaviors_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        inv = spec.invariants[0]
        assert inv.applies_to is AppliesTo.ALL_BEHAVIORS

    def test_applies_to_named_behaviors_parsed(self) -> None:
        src = '''agent A {
            behavior greet { must: x }
            invariant rule {
                applies_to: [greet]
                must: y
            }
        }'''
        spec = parse_source(src)
        inv = spec.invariants[0]
        assert inv.applies_to is AppliesTo.NAMED
        assert "greet" in inv.named_behaviors

    def test_severity_critical_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        assert spec.invariants[0].severity is Severity.CRITICAL

    @pytest.mark.parametrize("severity_str, expected", [
        ("high", Severity.HIGH),
        ("medium", Severity.MEDIUM),
        ("low", Severity.LOW),
        ("critical", Severity.CRITICAL),
    ])
    def test_severity_levels_parsed(self, severity_str: str, expected: Severity) -> None:
        src = f'agent A {{ invariant r {{ severity: {severity_str} must: x }} }}'
        spec = parse_source(src)
        assert spec.invariants[0].severity is expected

    def test_invariant_must_constraint_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        inv = spec.invariants[0]
        assert len(inv.constraints) == 1

    def test_invariant_must_not_constraint_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        inv = spec.invariants[0]
        assert len(inv.prohibitions) == 1


# ---------------------------------------------------------------------------
# Expression parsing
# ---------------------------------------------------------------------------


class TestExpressionParsing:
    def test_identifier_expression(self) -> None:
        src = 'agent A { behavior b { must: response } }'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, Identifier)
        assert expr.name == "response"

    def test_string_literal_expression(self) -> None:
        src = 'agent A { behavior b { must: "hello" } }'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, StringLit)
        assert expr.value == "hello"

    def test_number_literal_expression(self) -> None:
        src = 'agent A { behavior b { must: 42 } }'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, NumberLit)
        assert expr.value == 42.0

    def test_bool_literal_true(self) -> None:
        src = 'agent A { behavior b { must: true } }'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, BoolLit)
        assert expr.value is True

    def test_bool_literal_false(self) -> None:
        src = 'agent A { behavior b { must: false } }'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, BoolLit)
        assert expr.value is False

    def test_dot_access_expression(self) -> None:
        src = 'agent A { behavior b { must: response.status } }'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, DotAccess)
        assert expr.parts == ("response", "status")

    def test_function_call_expression(self) -> None:
        src = 'agent A { behavior b { must: len(items) } }'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, FunctionCall)
        assert expr.name == "len"
        assert len(expr.arguments) == 1

    def test_contains_expression(self) -> None:
        src = 'agent A { behavior b { must: response contains "error" } }'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, ContainsExpr)

    def test_in_list_expression(self) -> None:
        src = 'agent A { behavior b { must: status in [200, 201] } }'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, InListExpr)
        assert len(expr.items) == 2

    def test_before_expression(self) -> None:
        src = 'agent A { behavior b { must: auth before response } }'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, BeforeExpr)

    def test_after_expression(self) -> None:
        src = 'agent A { behavior b { must: response after auth } }'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, AfterExpr)

    def test_and_expression(self) -> None:
        src = 'agent A { behavior b { must: x and y } }'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, BinaryOpExpr)
        assert expr.op is BinOp.AND

    def test_or_expression(self) -> None:
        src = 'agent A { behavior b { must: x or y } }'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, BinaryOpExpr)
        assert expr.op is BinOp.OR

    def test_not_expression(self) -> None:
        src = 'agent A { behavior b { must: not harmful } }'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, UnaryOpExpr)
        assert expr.op is UnaryOpKind.NOT

    @pytest.mark.parametrize("op_str, expected_binop", [
        ("==", BinOp.EQ),
        ("!=", BinOp.NEQ),
        ("<", BinOp.LT),
        (">", BinOp.GT),
        ("<=", BinOp.LTE),
        (">=", BinOp.GTE),
    ])
    def test_comparison_operators(self, op_str: str, expected_binop: BinOp) -> None:
        src = f'agent A {{ behavior b {{ must: x {op_str} 1 }} }}'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, BinaryOpExpr)
        assert expr.op is expected_binop

    def test_parenthesized_expression(self) -> None:
        src = 'agent A { behavior b { must: (x and y) or z } }'
        spec = parse_source(src)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, BinaryOpExpr)
        assert expr.op is BinOp.OR

    def test_nested_and_or_precedence(self) -> None:
        src = 'agent A { behavior b { must: x or y and z } }'
        spec = parse_source(src)
        # y and z should bind tighter: x or (y and z)
        expr = spec.behaviors[0].must_constraints[0].expression
        assert isinstance(expr, BinaryOpExpr)
        assert expr.op is BinOp.OR


# ---------------------------------------------------------------------------
# Degradation and composition parsing
# ---------------------------------------------------------------------------


class TestDegradationAndCompositionParsing:
    def test_degradation_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        assert len(spec.degradations) == 1
        assert spec.degradations[0].fallback == "FallbackAgent"

    def test_receives_composition_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        receives = [c for c in spec.compositions if isinstance(c, Receives)]
        assert len(receives) == 1
        assert receives[0].source_agent == "InputAgent"

    def test_delegates_composition_parsed(self) -> None:
        spec = parse_source(FULL_AGENT)
        delegates = [c for c in spec.compositions if isinstance(c, Delegates)]
        assert len(delegates) == 1
        assert delegates[0].target_agent == "OutputAgent"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestParserErrors:
    def test_missing_agent_keyword_raises_error_collection(self) -> None:
        with pytest.raises(ParseErrorCollection):
            parse_source("NotAnAgent { }")

    def test_parse_error_collection_has_errors_flag(self) -> None:
        err = ParseErrorCollection()
        assert err.has_errors is False

    def test_parse_error_collection_str_no_errors(self) -> None:
        err = ParseErrorCollection()
        assert "no errors" in str(err).lower()

    def test_parse_error_collection_str_with_errors(self) -> None:
        with pytest.raises(ParseErrorCollection) as exc_info:
            parse_source("broken { }")
        assert len(exc_info.value.errors) > 0

    def test_recovery_strategy_enum_has_all_variants(self) -> None:
        for variant in ("SYNCHRONIZE", "SKIP_TOKEN", "INSERT_MISSING", "ABORT"):
            assert getattr(RecoveryStrategy, variant) is not None

    def test_parser_accepts_comments(self) -> None:
        src = '''agent A {
            // this is a comment
            behavior b {
                // another comment
                must: x
            }
        }'''
        spec = parse_source(src)
        assert spec.name == "A"

    def test_parser_accepts_block_comments(self) -> None:
        src = '''agent /* block */ A { behavior b { must: x } }'''
        spec = parse_source(src)
        assert spec.name == "A"
