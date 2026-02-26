"""Token definitions for the Behavioral Specification Language.

Defines the complete token vocabulary used by the BSL lexer.  Every
keyword, punctuation mark, and literal kind is represented as a member
of the ``TokenType`` enum, and every scanned token is represented by
a ``Token`` dataclass that carries its type, raw text, and source
position.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    """Exhaustive enumeration of all BSL token types."""

    # -----------------------------------------------------------------
    # Keywords — declaration
    # -----------------------------------------------------------------
    AGENT = auto()
    BEHAVIOR = auto()
    INVARIANT = auto()

    # -----------------------------------------------------------------
    # Keywords — constraint modalities
    # -----------------------------------------------------------------
    MUST = auto()
    MUST_NOT = auto()
    SHOULD = auto()
    MAY = auto()

    # -----------------------------------------------------------------
    # Keywords — conditional / structural
    # -----------------------------------------------------------------
    WHEN = auto()
    DEGRADES_TO = auto()
    DELEGATES_TO = auto()
    RECEIVES = auto()

    # -----------------------------------------------------------------
    # Keywords — metadata fields
    # -----------------------------------------------------------------
    VERSION = auto()
    MODEL = auto()
    OWNER = auto()
    CONFIDENCE = auto()
    LATENCY = auto()
    COST = auto()

    # -----------------------------------------------------------------
    # Keywords — special clauses
    # -----------------------------------------------------------------
    ESCALATE_TO_HUMAN = auto()
    AUDIT = auto()
    APPLIES_TO = auto()
    SEVERITY = auto()

    # -----------------------------------------------------------------
    # Keywords — set / collection operators
    # -----------------------------------------------------------------
    IN = auto()
    OF = auto()
    CASES = auto()
    ALL_BEHAVIORS = auto()

    # -----------------------------------------------------------------
    # Keywords — logical operators
    # -----------------------------------------------------------------
    AND = auto()
    OR = auto()
    NOT = auto()

    # -----------------------------------------------------------------
    # Keywords — temporal operators
    # -----------------------------------------------------------------
    BEFORE = auto()
    AFTER = auto()

    # -----------------------------------------------------------------
    # Keywords — string / list membership
    # -----------------------------------------------------------------
    CONTAINS = auto()

    # -----------------------------------------------------------------
    # Comparison operators
    # -----------------------------------------------------------------
    EQ = auto()       # ==
    NEQ = auto()      # !=
    LT = auto()       # <
    GT = auto()       # >
    LTE = auto()      # <=
    GTE = auto()      # >=

    # -----------------------------------------------------------------
    # Punctuation
    # -----------------------------------------------------------------
    COLON = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    DOT = auto()
    PERCENT = auto()

    # -----------------------------------------------------------------
    # Literals
    # -----------------------------------------------------------------
    STRING = auto()
    NUMBER = auto()
    BOOL = auto()

    # -----------------------------------------------------------------
    # Identifiers
    # -----------------------------------------------------------------
    IDENT = auto()

    # -----------------------------------------------------------------
    # Whitespace / structure
    # -----------------------------------------------------------------
    NEWLINE = auto()
    EOF = auto()
    COMMENT = auto()


# Mapping from literal keyword text to its TokenType.
KEYWORDS: dict[str, TokenType] = {
    "agent": TokenType.AGENT,
    "behavior": TokenType.BEHAVIOR,
    "invariant": TokenType.INVARIANT,
    "must": TokenType.MUST,
    "must_not": TokenType.MUST_NOT,
    "should": TokenType.SHOULD,
    "may": TokenType.MAY,
    "when": TokenType.WHEN,
    "degrades_to": TokenType.DEGRADES_TO,
    "delegates_to": TokenType.DELEGATES_TO,
    "receives": TokenType.RECEIVES,
    "version": TokenType.VERSION,
    "model": TokenType.MODEL,
    "owner": TokenType.OWNER,
    "confidence": TokenType.CONFIDENCE,
    "latency": TokenType.LATENCY,
    "cost": TokenType.COST,
    "escalate_to_human": TokenType.ESCALATE_TO_HUMAN,
    "audit": TokenType.AUDIT,
    "applies_to": TokenType.APPLIES_TO,
    "severity": TokenType.SEVERITY,
    "in": TokenType.IN,
    "of": TokenType.OF,
    "cases": TokenType.CASES,
    "all_behaviors": TokenType.ALL_BEHAVIORS,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
    "before": TokenType.BEFORE,
    "after": TokenType.AFTER,
    "contains": TokenType.CONTAINS,
    "true": TokenType.BOOL,
    "false": TokenType.BOOL,
}


@dataclass(frozen=True, slots=True)
class Token:
    """A single scanned token with source-location metadata.

    Parameters
    ----------
    type:
        The ``TokenType`` variant for this token.
    value:
        The raw text as it appeared in the source.
    line:
        1-based line number in the source file.
    col:
        1-based column number of the first character of the token.
    offset:
        0-based byte offset from the start of the source string.
    """

    type: TokenType
    value: str
    line: int
    col: int
    offset: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"

    @property
    def is_keyword(self) -> bool:
        """Return True if this token is any keyword (not an identifier or literal)."""
        non_keywords = {
            TokenType.STRING,
            TokenType.NUMBER,
            TokenType.BOOL,
            TokenType.IDENT,
            TokenType.NEWLINE,
            TokenType.EOF,
            TokenType.COMMENT,
            TokenType.COLON,
            TokenType.LBRACE,
            TokenType.RBRACE,
            TokenType.LBRACKET,
            TokenType.RBRACKET,
            TokenType.LPAREN,
            TokenType.RPAREN,
            TokenType.COMMA,
            TokenType.DOT,
            TokenType.PERCENT,
            TokenType.EQ,
            TokenType.NEQ,
            TokenType.LT,
            TokenType.GT,
            TokenType.LTE,
            TokenType.GTE,
        }
        return self.type not in non_keywords
