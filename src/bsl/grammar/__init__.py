"""BSL grammar module.

Exports token definitions and formal grammar constants.
"""
from __future__ import annotations

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
from bsl.grammar.tokens import KEYWORDS, Token, TokenType

__all__ = [
    # Token types
    "TokenType",
    "Token",
    "KEYWORDS",
    # Grammar constants
    "FULL_GRAMMAR",
    "GRAMMAR_ROOT",
    "GRAMMAR_METADATA",
    "GRAMMAR_BEHAVIOR",
    "GRAMMAR_THRESHOLD",
    "GRAMMAR_INVARIANT",
    "GRAMMAR_DEGRADATION",
    "GRAMMAR_COMPOSITION",
    "GRAMMAR_EXPRESSION",
    "BEHAVIOR_CLAUSE_ORDER",
    "INVARIANT_CLAUSE_ORDER",
    "AGENT_METADATA_ORDER",
]
