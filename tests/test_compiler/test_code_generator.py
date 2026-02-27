"""Unit tests for bsl.compiler.code_generator.

Each test exercises one AST node type → Python expression mapping.
Tests are fast, deterministic, and require no I/O.
"""
from __future__ import annotations

import pytest

from bsl.ast.nodes import (
    AfterExpr,
    BeforeExpr,
    BinOp,
    BinaryOpExpr,
    BoolLit,
    ContainsExpr,
    DotAccess,
    FunctionCall,
    Identifier,
    InListExpr,
    NumberLit,
    StringLit,
    UnaryOpExpr,
    UnaryOpKind,
    Span,
)
from bsl.compiler.code_generator import CodeGenerator

# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

DUMMY_SPAN = Span(start=0, end=1, line=1, col=1)


def _ident(name: str) -> Identifier:
    return Identifier(name=name, span=DUMMY_SPAN)


def _str(value: str) -> StringLit:
    return StringLit(value=value, span=DUMMY_SPAN)


def _num(value: float) -> NumberLit:
    return NumberLit(value=value, span=DUMMY_SPAN)


def _bool(value: bool) -> BoolLit:
    return BoolLit(value=value, span=DUMMY_SPAN)


def _dot(*parts: str) -> DotAccess:
    return DotAccess(parts=tuple(parts), span=DUMMY_SPAN)


def _binop(op: BinOp, left: object, right: object) -> BinaryOpExpr:
    return BinaryOpExpr(op=op, left=left, right=right, span=DUMMY_SPAN)  # type: ignore[arg-type]


def _unary_not(operand: object) -> UnaryOpExpr:
    return UnaryOpExpr(op=UnaryOpKind.NOT, operand=operand, span=DUMMY_SPAN)  # type: ignore[arg-type]


def _contains(subject: object, value: object) -> ContainsExpr:
    return ContainsExpr(subject=subject, value=value, span=DUMMY_SPAN)  # type: ignore[arg-type]


def _in_list(subject: object, *items: object) -> InListExpr:
    return InListExpr(subject=subject, items=tuple(items), span=DUMMY_SPAN)  # type: ignore[arg-type]


def _before(left: object, right: object) -> BeforeExpr:
    return BeforeExpr(left=left, right=right, span=DUMMY_SPAN)  # type: ignore[arg-type]


def _after(left: object, right: object) -> AfterExpr:
    return AfterExpr(left=left, right=right, span=DUMMY_SPAN)  # type: ignore[arg-type]


def _func(name: str, *args: object) -> FunctionCall:
    return FunctionCall(name=name, arguments=tuple(args), span=DUMMY_SPAN)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def gen() -> CodeGenerator:
    """Return a fresh CodeGenerator instance."""
    return CodeGenerator()


# ---------------------------------------------------------------------------
# Literal tests
# ---------------------------------------------------------------------------


class TestLiterals:
    def test_string_literal_single_word(self, gen: CodeGenerator) -> None:
        result = gen.generate(_str("Hello"))
        assert result == "'Hello'"

    def test_string_literal_with_special_chars(self, gen: CodeGenerator) -> None:
        result = gen.generate(_str("it's a test"))
        assert "it's a test" in result

    def test_number_literal_integer(self, gen: CodeGenerator) -> None:
        result = gen.generate(_num(42.0))
        assert result == "42"

    def test_number_literal_float(self, gen: CodeGenerator) -> None:
        result = gen.generate(_num(3.14))
        assert result == "3.14"

    def test_number_literal_zero(self, gen: CodeGenerator) -> None:
        result = gen.generate(_num(0.0))
        assert result == "0"

    def test_bool_literal_true(self, gen: CodeGenerator) -> None:
        result = gen.generate(_bool(True))
        assert result == "True"

    def test_bool_literal_false(self, gen: CodeGenerator) -> None:
        result = gen.generate(_bool(False))
        assert result == "False"


# ---------------------------------------------------------------------------
# Identifier and DotAccess tests
# ---------------------------------------------------------------------------


class TestIdentifiersAndDotAccess:
    def test_identifier(self, gen: CodeGenerator) -> None:
        result = gen.generate(_ident("response"))
        assert result == "response"

    def test_dot_access_two_parts(self, gen: CodeGenerator) -> None:
        result = gen.generate(_dot("response", "tone"))
        assert result == "response.tone"

    def test_dot_access_three_parts(self, gen: CodeGenerator) -> None:
        result = gen.generate(_dot("agent", "session", "id"))
        assert result == "agent.session.id"


# ---------------------------------------------------------------------------
# BinaryOpExpr tests
# ---------------------------------------------------------------------------


class TestBinaryOp:
    def test_equality(self, gen: CodeGenerator) -> None:
        expr = _binop(BinOp.EQ, _dot("response", "tone"), _str("warm"))
        result = gen.generate(expr)
        assert result == "response.tone == 'warm'"

    def test_not_equal(self, gen: CodeGenerator) -> None:
        expr = _binop(BinOp.NEQ, _ident("status"), _num(500.0))
        result = gen.generate(expr)
        assert result == "status != 500"

    def test_less_than(self, gen: CodeGenerator) -> None:
        expr = _binop(BinOp.LT, _ident("latency"), _num(1000.0))
        result = gen.generate(expr)
        assert result == "latency < 1000"

    def test_greater_than(self, gen: CodeGenerator) -> None:
        expr = _binop(BinOp.GT, _ident("score"), _num(0.8))
        result = gen.generate(expr)
        assert result == "score > 0.8"

    def test_less_than_or_equal(self, gen: CodeGenerator) -> None:
        expr = _binop(BinOp.LTE, _ident("cost"), _num(10.0))
        result = gen.generate(expr)
        assert result == "cost <= 10"

    def test_greater_than_or_equal(self, gen: CodeGenerator) -> None:
        expr = _binop(BinOp.GTE, _ident("confidence"), _num(0.9))
        result = gen.generate(expr)
        assert result == "confidence >= 0.9"

    def test_logical_and(self, gen: CodeGenerator) -> None:
        left = _binop(BinOp.EQ, _ident("a"), _num(1.0))
        right = _binop(BinOp.EQ, _ident("b"), _num(2.0))
        expr = _binop(BinOp.AND, left, right)
        result = gen.generate(expr)
        assert " and " in result

    def test_logical_or(self, gen: CodeGenerator) -> None:
        left = _binop(BinOp.EQ, _ident("x"), _num(1.0))
        right = _binop(BinOp.EQ, _ident("y"), _num(2.0))
        expr = _binop(BinOp.OR, left, right)
        result = gen.generate(expr)
        assert " or " in result


# ---------------------------------------------------------------------------
# UnaryOpExpr tests
# ---------------------------------------------------------------------------


class TestUnaryOp:
    def test_not_identifier(self, gen: CodeGenerator) -> None:
        expr = _unary_not(_ident("flagged"))
        result = gen.generate(expr)
        assert result == "not flagged"

    def test_not_binary_expression(self, gen: CodeGenerator) -> None:
        inner = _binop(BinOp.EQ, _ident("a"), _ident("b"))
        expr = _unary_not(inner)
        result = gen.generate(expr)
        assert result.startswith("not (")

    def test_not_contains_expression(self, gen: CodeGenerator) -> None:
        inner = _contains(_ident("response"), _str("error"))
        expr = _unary_not(inner)
        result = gen.generate(expr)
        assert result.startswith("not (")


# ---------------------------------------------------------------------------
# ContainsExpr tests
# ---------------------------------------------------------------------------


class TestContainsExpr:
    def test_string_contains(self, gen: CodeGenerator) -> None:
        expr = _contains(_ident("response"), _str("Hello"))
        result = gen.generate(expr)
        assert result == "'Hello' in response"

    def test_identifier_contains(self, gen: CodeGenerator) -> None:
        expr = _contains(_ident("response"), _ident("customer_name"))
        result = gen.generate(expr)
        assert result == "customer_name in response"

    def test_dot_access_contains(self, gen: CodeGenerator) -> None:
        expr = _contains(_dot("response", "text"), _str("apology"))
        result = gen.generate(expr)
        assert result == "'apology' in response.text"


# ---------------------------------------------------------------------------
# InListExpr tests
# ---------------------------------------------------------------------------


class TestInListExpr:
    def test_in_list_strings(self, gen: CodeGenerator) -> None:
        expr = _in_list(_ident("status"), _str("active"), _str("pending"))
        result = gen.generate(expr)
        assert "status in" in result
        assert "'active'" in result
        assert "'pending'" in result

    def test_in_list_numbers(self, gen: CodeGenerator) -> None:
        expr = _in_list(_ident("code"), _num(200.0), _num(201.0))
        result = gen.generate(expr)
        assert "code in" in result
        assert "200" in result
        assert "201" in result

    def test_in_list_single_item(self, gen: CodeGenerator) -> None:
        expr = _in_list(_ident("level"), _str("high"))
        result = gen.generate(expr)
        assert "level in" in result


# ---------------------------------------------------------------------------
# Temporal expression tests
# ---------------------------------------------------------------------------


class TestTemporalExpressions:
    def test_before_expression(self, gen: CodeGenerator) -> None:
        expr = _before(_ident("auth"), _ident("process"))
        result = gen.generate(expr)
        assert result == "_bsl_before(auth, process)"

    def test_after_expression(self, gen: CodeGenerator) -> None:
        expr = _after(_ident("response"), _ident("validation"))
        result = gen.generate(expr)
        assert result == "_bsl_after(response, validation)"


# ---------------------------------------------------------------------------
# FunctionCall tests
# ---------------------------------------------------------------------------


class TestFunctionCall:
    def test_len_function(self, gen: CodeGenerator) -> None:
        expr = _func("len", _ident("items"))
        result = gen.generate(expr)
        assert result == "len(items)"

    def test_matches_function(self, gen: CodeGenerator) -> None:
        # r"\d+" is the 3-char string \d+ — repr() produces '\\d+',
        # which as a Python string value is: matches(text, '\\d+')
        # In the assertion literal we need four backslash chars in source
        # to represent two backslashes in the expected string value.
        expr = _func("matches", _ident("text"), _str(r"\d+"))
        result = gen.generate(expr)
        assert result == "matches(text, '\\\\d+')"

    def test_function_no_args(self, gen: CodeGenerator) -> None:
        expr = _func("get_token")
        result = gen.generate(expr)
        assert result == "get_token()"

    def test_function_multiple_args(self, gen: CodeGenerator) -> None:
        expr = _func("check", _ident("a"), _ident("b"), _ident("c"))
        result = gen.generate(expr)
        assert result == "check(a, b, c)"


# ---------------------------------------------------------------------------
# Assertion generation tests
# ---------------------------------------------------------------------------


class TestAssertionGeneration:
    def test_generate_assertion_positive(self, gen: CodeGenerator) -> None:
        expr = _binop(BinOp.EQ, _dot("response", "status"), _num(200.0))
        result = gen.generate_assertion(expr)
        assert result.startswith("assert ")
        assert "==" in result

    def test_generate_negated_assertion(self, gen: CodeGenerator) -> None:
        expr = _contains(_ident("response"), _str("error"))
        result = gen.generate_negated_assertion(expr)
        assert result.startswith("assert not ")

    def test_assertion_and_expression_are_consistent(self, gen: CodeGenerator) -> None:
        expr = _contains(_ident("text"), _str("Hello"))
        py_expr = gen.generate(expr)
        assertion = gen.generate_assertion(expr)
        assert assertion == f"assert {py_expr}"

    def test_negated_assertion_wraps_expression(self, gen: CodeGenerator) -> None:
        expr = _contains(_ident("text"), _str("bad"))
        assertion = gen.generate_negated_assertion(expr)
        assert "assert not" in assertion


# ---------------------------------------------------------------------------
# Idempotency tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_same_input_same_output(self, gen: CodeGenerator) -> None:
        expr = _binop(BinOp.EQ, _dot("response", "tone"), _str("warm"))
        first = gen.generate(expr)
        second = gen.generate(expr)
        assert first == second

    def test_multiple_calls_consistent(self, gen: CodeGenerator) -> None:
        expr = _contains(_ident("response"), _str("Hello"))
        results = [gen.generate(expr) for _ in range(5)]
        assert len(set(results)) == 1
