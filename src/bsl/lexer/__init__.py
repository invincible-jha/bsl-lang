"""BSL Lexer module.

Exports the ``Lexer`` class and the ``tokenize`` convenience function.
"""
from __future__ import annotations

from bsl.lexer.lexer import LexError, Lexer, tokenize

__all__ = ["Lexer", "tokenize", "LexError"]
