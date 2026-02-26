"""Unit tests for bsl.lexer — tokenization of BSL source text."""
from __future__ import annotations

import pytest

from bsl.grammar.tokens import TokenType
from bsl.lexer.lexer import LexError, Lexer, tokenize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def types_of(tokens: list) -> list[TokenType]:
    """Return just the token types, excluding EOF."""
    return [t.type for t in tokens if t.type != TokenType.EOF]


def non_structural_types(tokens: list) -> list[TokenType]:
    """Exclude NEWLINE, COMMENT, and EOF tokens."""
    excluded = {TokenType.NEWLINE, TokenType.COMMENT, TokenType.EOF}
    return [t.type for t in tokens if t.type not in excluded]


# ---------------------------------------------------------------------------
# Empty and whitespace-only inputs
# ---------------------------------------------------------------------------


class TestEmptyInputs:
    def test_empty_string_produces_only_eof(self) -> None:
        tokens = tokenize("")
        assert len(tokens) == 1
        assert tokens[0].type is TokenType.EOF

    def test_whitespace_only_produces_only_eof(self) -> None:
        tokens = tokenize("   \t  ")
        result = [t for t in tokens if t.type != TokenType.EOF]
        assert result == []

    def test_newline_only_produces_newline_and_eof(self) -> None:
        tokens = tokenize("\n")
        assert tokens[0].type is TokenType.NEWLINE
        assert tokens[-1].type is TokenType.EOF


# ---------------------------------------------------------------------------
# Keyword tokenization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source, expected_type", [
    ("agent", TokenType.AGENT),
    ("behavior", TokenType.BEHAVIOR),
    ("invariant", TokenType.INVARIANT),
    ("must", TokenType.MUST),
    ("must_not", TokenType.MUST_NOT),
    ("should", TokenType.SHOULD),
    ("may", TokenType.MAY),
    ("when", TokenType.WHEN),
    ("degrades_to", TokenType.DEGRADES_TO),
    ("delegates_to", TokenType.DELEGATES_TO),
    ("receives", TokenType.RECEIVES),
    ("version", TokenType.VERSION),
    ("model", TokenType.MODEL),
    ("owner", TokenType.OWNER),
    ("confidence", TokenType.CONFIDENCE),
    ("latency", TokenType.LATENCY),
    ("cost", TokenType.COST),
    ("escalate_to_human", TokenType.ESCALATE_TO_HUMAN),
    ("audit", TokenType.AUDIT),
    ("applies_to", TokenType.APPLIES_TO),
    ("severity", TokenType.SEVERITY),
    ("in", TokenType.IN),
    ("of", TokenType.OF),
    ("cases", TokenType.CASES),
    ("all_behaviors", TokenType.ALL_BEHAVIORS),
    ("and", TokenType.AND),
    ("or", TokenType.OR),
    ("not", TokenType.NOT),
    ("before", TokenType.BEFORE),
    ("after", TokenType.AFTER),
    ("contains", TokenType.CONTAINS),
    ("true", TokenType.BOOL),
    ("false", TokenType.BOOL),
])
def test_keyword_produces_correct_token_type(source: str, expected_type: TokenType) -> None:
    tokens = tokenize(source)
    significant = [t for t in tokens if t.type != TokenType.EOF]
    assert len(significant) == 1
    assert significant[0].type is expected_type
    assert significant[0].value == source


def test_none_keyword_is_emitted_as_ident() -> None:
    tokens = tokenize("none")
    significant = [t for t in tokens if t.type != TokenType.EOF]
    assert significant[0].type is TokenType.IDENT
    assert significant[0].value == "none"


# ---------------------------------------------------------------------------
# Identifier tokenization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ident", [
    "myAgent",
    "_private",
    "snake_case",
    "PascalCase",
    "with_123_digits",
    "a",
])
def test_identifier_tokenized_as_ident(ident: str) -> None:
    tokens = tokenize(ident)
    significant = [t for t in tokens if t.type != TokenType.EOF]
    assert significant[0].type is TokenType.IDENT
    assert significant[0].value == ident


# ---------------------------------------------------------------------------
# Number tokenization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source, expected_value", [
    ("0", "0"),
    ("42", "42"),
    ("3.14", "3.14"),
    ("100", "100"),
    ("0.5", "0.5"),
    ("99.9", "99.9"),
])
def test_number_tokenized_correctly(source: str, expected_value: str) -> None:
    tokens = tokenize(source)
    significant = [t for t in tokens if t.type != TokenType.EOF]
    assert significant[0].type is TokenType.NUMBER
    assert significant[0].value == expected_value


# ---------------------------------------------------------------------------
# String literal tokenization
# ---------------------------------------------------------------------------


def test_simple_string_literal() -> None:
    tokens = tokenize('"hello"')
    significant = [t for t in tokens if t.type != TokenType.EOF]
    assert significant[0].type is TokenType.STRING
    assert significant[0].value == "hello"


def test_string_with_escape_newline() -> None:
    tokens = tokenize(r'"line1\nline2"')
    significant = [t for t in tokens if t.type != TokenType.EOF]
    assert significant[0].type is TokenType.STRING
    assert "\n" in significant[0].value


def test_string_with_escape_tab() -> None:
    tokens = tokenize(r'"col1\tcol2"')
    significant = [t for t in tokens if t.type != TokenType.EOF]
    assert "\t" in significant[0].value


def test_string_with_escaped_quote() -> None:
    tokens = tokenize(r'"say \"hi\""')
    significant = [t for t in tokens if t.type != TokenType.EOF]
    assert '"' in significant[0].value


def test_empty_string_literal() -> None:
    tokens = tokenize('""')
    significant = [t for t in tokens if t.type != TokenType.EOF]
    assert significant[0].type is TokenType.STRING
    assert significant[0].value == ""


def test_unterminated_string_raises_lex_error() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize('"no closing quote')
    assert exc_info.value.line >= 1


def test_newline_inside_string_raises_lex_error() -> None:
    with pytest.raises(LexError):
        tokenize('"line1\nline2"')


# ---------------------------------------------------------------------------
# Operator tokenization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source, expected_type, expected_value", [
    ("==", TokenType.EQ, "=="),
    ("!=", TokenType.NEQ, "!="),
    ("<=", TokenType.LTE, "<="),
    (">=", TokenType.GTE, ">="),
    ("<", TokenType.LT, "<"),
    (">", TokenType.GT, ">"),
    (":", TokenType.COLON, ":"),
    ("{", TokenType.LBRACE, "{"),
    ("}", TokenType.RBRACE, "}"),
    ("[", TokenType.LBRACKET, "["),
    ("]", TokenType.RBRACKET, "]"),
    ("(", TokenType.LPAREN, "("),
    (")", TokenType.RPAREN, ")"),
    (",", TokenType.COMMA, ","),
    (".", TokenType.DOT, "."),
    ("%", TokenType.PERCENT, "%"),
])
def test_operator_tokenized_correctly(
    source: str, expected_type: TokenType, expected_value: str
) -> None:
    tokens = tokenize(source)
    significant = [t for t in tokens if t.type != TokenType.EOF]
    assert significant[0].type is expected_type
    assert significant[0].value == expected_value


# ---------------------------------------------------------------------------
# Comment handling
# ---------------------------------------------------------------------------


def test_line_comment_emitted_as_comment_token() -> None:
    tokens = tokenize("// this is a comment")
    comment_tokens = [t for t in tokens if t.type is TokenType.COMMENT]
    assert len(comment_tokens) == 1
    assert "this is a comment" in comment_tokens[0].value


def test_block_comment_emitted_as_comment_token() -> None:
    tokens = tokenize("/* block comment */")
    comment_tokens = [t for t in tokens if t.type is TokenType.COMMENT]
    assert len(comment_tokens) == 1
    assert "block comment" in comment_tokens[0].value


def test_unterminated_block_comment_raises_lex_error() -> None:
    with pytest.raises(LexError):
        tokenize("/* never closed")


def test_multiline_block_comment() -> None:
    source = "/* line one\nline two */"
    tokens = tokenize(source)
    comment_tokens = [t for t in tokens if t.type is TokenType.COMMENT]
    assert len(comment_tokens) == 1


# ---------------------------------------------------------------------------
# Source location tracking
# ---------------------------------------------------------------------------


def test_first_token_has_line_1_col_1() -> None:
    tokens = tokenize("agent")
    assert tokens[0].line == 1
    assert tokens[0].col == 1


def test_token_on_second_line_has_correct_line_number() -> None:
    tokens = tokenize("agent\nbehavior")
    behavior_tok = next(t for t in tokens if t.type is TokenType.BEHAVIOR)
    assert behavior_tok.line == 2


def test_token_offset_is_zero_for_first_token() -> None:
    tokens = tokenize("agent")
    assert tokens[0].offset == 0


def test_offset_advances_correctly() -> None:
    tokens = tokenize("agent MyAgent")
    ident_tok = next(t for t in tokens if t.type is TokenType.IDENT)
    assert ident_tok.offset == 6


# ---------------------------------------------------------------------------
# Full agent snippet
# ---------------------------------------------------------------------------


def test_tokenize_minimal_agent_snippet() -> None:
    source = 'agent MyAgent { version: "1.0" }'
    tokens = tokenize(source)
    significant = non_structural_types(tokens)
    assert TokenType.AGENT in significant
    assert TokenType.IDENT in significant
    assert TokenType.LBRACE in significant
    assert TokenType.VERSION in significant
    assert TokenType.COLON in significant
    assert TokenType.STRING in significant
    assert TokenType.RBRACE in significant
    assert TokenType.EOF in [t.type for t in tokens]


def test_invalid_character_raises_lex_error() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("agent @ name")
    assert exc_info.value.col >= 1
    assert "@" in str(exc_info.value)


def test_lex_error_carries_position_info() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("agent MyAgent { @ }")
    err = exc_info.value
    assert isinstance(err.line, int)
    assert isinstance(err.col, int)
    assert isinstance(err.offset, int)


def test_module_level_tokenize_function_returns_list() -> None:
    result = tokenize("agent")
    assert isinstance(result, list)
    assert len(result) > 0
