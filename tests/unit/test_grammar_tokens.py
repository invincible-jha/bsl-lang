"""Unit tests for bsl.grammar.tokens — TokenType enum and Token dataclass."""
from __future__ import annotations

import pytest

from bsl.grammar.tokens import KEYWORDS, Token, TokenType


# ---------------------------------------------------------------------------
# TokenType enum membership
# ---------------------------------------------------------------------------


class TestTokenTypeEnum:
    def test_all_keywords_have_corresponding_token_types(self) -> None:
        keyword_token_types = {
            TokenType.AGENT, TokenType.BEHAVIOR, TokenType.INVARIANT,
            TokenType.MUST, TokenType.MUST_NOT, TokenType.SHOULD, TokenType.MAY,
            TokenType.WHEN, TokenType.DEGRADES_TO, TokenType.DELEGATES_TO,
            TokenType.RECEIVES, TokenType.VERSION, TokenType.MODEL, TokenType.OWNER,
            TokenType.CONFIDENCE, TokenType.LATENCY, TokenType.COST,
            TokenType.ESCALATE_TO_HUMAN, TokenType.AUDIT, TokenType.APPLIES_TO,
            TokenType.SEVERITY, TokenType.IN, TokenType.OF, TokenType.CASES,
            TokenType.ALL_BEHAVIORS, TokenType.AND, TokenType.OR, TokenType.NOT,
            TokenType.BEFORE, TokenType.AFTER, TokenType.CONTAINS,
        }
        for name, member in TokenType.__members__.items():
            _ = name  # suppress unused warning
            _ = member

    def test_token_type_members_are_unique(self) -> None:
        values = [t.value for t in TokenType]
        assert len(values) == len(set(values))

    def test_comparison_operators_exist(self) -> None:
        assert TokenType.EQ is not None
        assert TokenType.NEQ is not None
        assert TokenType.LT is not None
        assert TokenType.GT is not None
        assert TokenType.LTE is not None
        assert TokenType.GTE is not None

    def test_punctuation_tokens_exist(self) -> None:
        for ttype in (
            TokenType.COLON, TokenType.LBRACE, TokenType.RBRACE,
            TokenType.LBRACKET, TokenType.RBRACKET,
            TokenType.LPAREN, TokenType.RPAREN,
            TokenType.COMMA, TokenType.DOT, TokenType.PERCENT,
        ):
            assert isinstance(ttype, TokenType)

    def test_literal_tokens_exist(self) -> None:
        for ttype in (TokenType.STRING, TokenType.NUMBER, TokenType.BOOL):
            assert isinstance(ttype, TokenType)

    def test_structural_tokens_exist(self) -> None:
        for ttype in (TokenType.NEWLINE, TokenType.EOF, TokenType.COMMENT):
            assert isinstance(ttype, TokenType)


# ---------------------------------------------------------------------------
# KEYWORDS mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("keyword, expected_type", [
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
def test_keywords_map_correct_type(keyword: str, expected_type: TokenType) -> None:
    assert KEYWORDS[keyword] is expected_type


def test_keywords_dict_is_nonempty() -> None:
    assert len(KEYWORDS) > 0


def test_unknown_word_not_in_keywords() -> None:
    assert "foobar" not in KEYWORDS
    assert "none" not in KEYWORDS


# ---------------------------------------------------------------------------
# Token dataclass
# ---------------------------------------------------------------------------


class TestToken:
    def test_token_creation(self) -> None:
        tok = Token(type=TokenType.IDENT, value="hello", line=1, col=1, offset=0)
        assert tok.type is TokenType.IDENT
        assert tok.value == "hello"
        assert tok.line == 1
        assert tok.col == 1
        assert tok.offset == 0

    def test_token_is_frozen(self) -> None:
        tok = Token(type=TokenType.IDENT, value="x", line=1, col=1, offset=0)
        with pytest.raises((AttributeError, TypeError)):
            tok.value = "y"  # type: ignore[misc]

    def test_token_repr_format(self) -> None:
        tok = Token(type=TokenType.AGENT, value="agent", line=3, col=5, offset=10)
        r = repr(tok)
        assert "AGENT" in r
        assert "agent" in r
        assert "3:5" in r

    def test_token_is_keyword_for_agent(self) -> None:
        tok = Token(type=TokenType.AGENT, value="agent", line=1, col=1, offset=0)
        assert tok.is_keyword is True

    def test_token_is_keyword_for_must(self) -> None:
        tok = Token(type=TokenType.MUST, value="must", line=1, col=1, offset=0)
        assert tok.is_keyword is True

    def test_token_is_not_keyword_for_ident(self) -> None:
        tok = Token(type=TokenType.IDENT, value="myVar", line=1, col=1, offset=0)
        assert tok.is_keyword is False

    def test_token_is_not_keyword_for_string(self) -> None:
        tok = Token(type=TokenType.STRING, value="hello", line=1, col=1, offset=0)
        assert tok.is_keyword is False

    def test_token_is_not_keyword_for_number(self) -> None:
        tok = Token(type=TokenType.NUMBER, value="42", line=1, col=1, offset=0)
        assert tok.is_keyword is False

    def test_token_is_not_keyword_for_eof(self) -> None:
        tok = Token(type=TokenType.EOF, value="", line=10, col=1, offset=100)
        assert tok.is_keyword is False

    def test_token_is_not_keyword_for_punctuation(self) -> None:
        for ttype, val in [
            (TokenType.COLON, ":"), (TokenType.LBRACE, "{"), (TokenType.RBRACE, "}"),
            (TokenType.COMMA, ","), (TokenType.DOT, "."),
        ]:
            tok = Token(type=ttype, value=val, line=1, col=1, offset=0)
            assert tok.is_keyword is False

    def test_token_equality_by_value(self) -> None:
        tok_a = Token(type=TokenType.IDENT, value="x", line=1, col=1, offset=0)
        tok_b = Token(type=TokenType.IDENT, value="x", line=1, col=1, offset=0)
        assert tok_a == tok_b

    def test_token_inequality_on_different_value(self) -> None:
        tok_a = Token(type=TokenType.IDENT, value="x", line=1, col=1, offset=0)
        tok_b = Token(type=TokenType.IDENT, value="y", line=1, col=1, offset=0)
        assert tok_a != tok_b
