"""BSL Parser module.

Exports the ``Parser`` class, the ``parse`` convenience function, and
parse error types.
"""
from __future__ import annotations

from bsl.parser.errors import ParseError, ParseErrorCollection, RecoveryStrategy
from bsl.parser.parser import Parser, parse

__all__ = [
    "Parser",
    "parse",
    "ParseError",
    "ParseErrorCollection",
    "RecoveryStrategy",
]
