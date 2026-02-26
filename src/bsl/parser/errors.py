"""Parse error types for the BSL parser.

All parse errors carry source-location information so that the CLI and
editor integrations can display precise, actionable error messages.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from bsl.ast.nodes import Span
from bsl.grammar.tokens import Token, TokenType


class RecoveryStrategy(Enum):
    """How the parser should attempt to continue after an error.

    SYNCHRONIZE
        Skip tokens until a synchronization point (``}`` or EOF) is
        found, then resume parsing from the next top-level declaration.
    SKIP_TOKEN
        Consume the unexpected token and continue parsing from the next
        position — suitable for minor single-token errors.
    INSERT_MISSING
        Pretend a missing token was present and continue parsing —
        suitable for optional clauses or missing colons.
    ABORT
        Stop parsing immediately and return what has been collected.
    """

    SYNCHRONIZE = auto()
    SKIP_TOKEN = auto()
    INSERT_MISSING = auto()
    ABORT = auto()


@dataclass(frozen=True)
class ParseError(Exception):
    """A single parse error with location and recovery hint.

    Parameters
    ----------
    message:
        Human-readable description of the error.
    span:
        Source location of the offending token or region.
    expected:
        What token types were expected at this position.
    found:
        The actual token that was encountered, if available.
    recovery:
        Suggested recovery strategy for the parser's error handler.
    """

    message: str
    span: Span
    expected: tuple[TokenType, ...]
    found: Token | None
    recovery: RecoveryStrategy

    def __str__(self) -> str:
        loc = f"{self.span.line}:{self.span.col}"
        if self.found is not None:
            return (
                f"ParseError at {loc}: {self.message} "
                f"(found {self.found.type.name} {self.found.value!r})"
            )
        return f"ParseError at {loc}: {self.message}"

    # dataclass(frozen=True) doesn't call Exception.__init__ automatically
    def __post_init__(self) -> None:
        # Call Exception.__init__ so the error has the right args
        object.__setattr__(self, "args", (str(self),))


@dataclass
class ParseErrorCollection(Exception):
    """Aggregates multiple ``ParseError`` instances from a single parse run.

    The parser continues past errors using recovery strategies and
    collects them all rather than aborting at the first problem.

    Parameters
    ----------
    errors:
        Ordered list of errors encountered during parsing.
    """

    errors: list[ParseError] = field(default_factory=list)

    def add(self, error: ParseError) -> None:
        """Append a new error to the collection."""
        self.errors.append(error)

    @property
    def has_errors(self) -> bool:
        """Return True if any errors were recorded."""
        return bool(self.errors)

    def __str__(self) -> str:
        if not self.errors:
            return "ParseErrorCollection (no errors)"
        lines = [f"ParseErrorCollection ({len(self.errors)} error(s)):"]
        for err in self.errors:
            lines.append(f"  {err}")
        return "\n".join(lines)
