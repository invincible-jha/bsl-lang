"""BSL Lexer: converts raw source text into a flat list of tokens.

The lexer is a single-pass character scanner that produces a
``list[Token]`` from a BSL source string.  It tracks line and column
numbers for every token so the parser and validator can produce
precise error messages.

Comment styles supported:
    - ``//`` single-line comments (run to end of line)
    - ``/* ... */`` block comments (may span multiple lines)

String literals are double-quoted and support standard backslash
escapes: ``\\n``, ``\\t``, ``\\r``, ``\\\\ ``, ``\\"``

Numbers are integers or floats (``-`` sign is handled by the parser
as a unary operator, not as part of the literal).

Identifiers follow the pattern ``[A-Za-z_][A-Za-z0-9_]*`` and are
checked against the keyword table; matching identifiers are emitted
as their corresponding keyword token type.
"""
from __future__ import annotations

import re
from typing import Final

from bsl.grammar.tokens import KEYWORDS, Token, TokenType

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_IDENT_START: Final[re.Pattern[str]] = re.compile(r"[A-Za-z_]")
_IDENT_CONT: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9_]")
_DIGIT: Final[re.Pattern[str]] = re.compile(r"[0-9]")

_ESCAPE_MAP: Final[dict[str, str]] = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "\\": "\\",
    '"': '"',
    "'": "'",
    "0": "\0",
}


class LexError(Exception):
    """Raised when the lexer encounters invalid input.

    Parameters
    ----------
    message:
        Human-readable description of the problem.
    line:
        1-based line number where the error occurred.
    col:
        1-based column number where the error occurred.
    offset:
        0-based byte offset in the source where the error occurred.
    """

    def __init__(self, message: str, line: int, col: int, offset: int) -> None:
        super().__init__(f"LexError at {line}:{col}: {message}")
        self.lex_message = message
        self.line = line
        self.col = col
        self.offset = offset


class Lexer:
    """Single-pass BSL lexer.

    Parameters
    ----------
    source:
        The complete BSL source text to tokenize.
    """

    __slots__ = ("_source", "_pos", "_line", "_col", "_tokens", "_token_line", "_token_col")

    def __init__(self, source: str) -> None:
        self._source: str = source
        self._pos: int = 0
        self._line: int = 1
        self._col: int = 1
        self._tokens: list[Token] = []
        self._token_line: int = 1
        self._token_col: int = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tokenize(self) -> list[Token]:
        """Scan the entire source and return the complete token list.

        The list always ends with an ``EOF`` token.

        Returns
        -------
        list[Token]
            Ordered list of tokens (COMMENT tokens are included).

        Raises
        ------
        LexError
            On any character that cannot begin a valid token.
        """
        while self._pos < len(self._source):
            self._scan_one()
        self._emit(TokenType.EOF, "", self._pos)
        return self._tokens

    # ------------------------------------------------------------------
    # Internal scanner
    # ------------------------------------------------------------------

    def _current(self) -> str:
        """Return the character at the current position without advancing."""
        return self._source[self._pos] if self._pos < len(self._source) else ""

    def _peek(self, offset: int = 1) -> str:
        """Return the character at ``pos + offset`` without advancing."""
        idx = self._pos + offset
        return self._source[idx] if idx < len(self._source) else ""

    def _advance(self) -> str:
        """Consume and return the current character, updating line/col."""
        ch = self._source[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return ch

    def _emit(self, token_type: TokenType, value: str, start_offset: int) -> None:
        """Append a token using the recorded start position."""
        # We store the line/col at the *start* of the token.
        # Because _advance() already moved the position, we need the
        # snapshot that was taken before scanning began.
        self._tokens.append(
            Token(
                type=token_type,
                value=value,
                line=self._token_line,
                col=self._token_col,
                offset=start_offset,
            )
        )

    def _scan_one(self) -> None:
        """Scan exactly one token (or skip whitespace/comments)."""
        self._token_line = self._line
        self._token_col = self._col
        start = self._pos
        ch = self._current()

        # Whitespace (skip, but track newlines as tokens for error recovery)
        if ch in (" ", "\t", "\r"):
            self._advance()
            return

        if ch == "\n":
            self._advance()
            self._emit(TokenType.NEWLINE, "\n", start)
            return

        # Comments
        if ch == "/" and self._peek() == "/":
            self._scan_line_comment(start)
            return
        if ch == "/" and self._peek() == "*":
            self._scan_block_comment(start)
            return

        # String literals
        if ch == '"':
            self._scan_string(start)
            return

        # Numbers
        if _DIGIT.match(ch):
            self._scan_number(start)
            return

        # Identifiers and keywords
        if _IDENT_START.match(ch):
            self._scan_ident_or_keyword(start)
            return

        # Two-character operators
        if ch == "=" and self._peek() == "=":
            self._advance()
            self._advance()
            self._emit(TokenType.EQ, "==", start)
            return
        if ch == "!" and self._peek() == "=":
            self._advance()
            self._advance()
            self._emit(TokenType.NEQ, "!=", start)
            return
        if ch == "<" and self._peek() == "=":
            self._advance()
            self._advance()
            self._emit(TokenType.LTE, "<=", start)
            return
        if ch == ">" and self._peek() == "=":
            self._advance()
            self._advance()
            self._emit(TokenType.GTE, ">=", start)
            return

        # Single-character operators / punctuation
        single: dict[str, TokenType] = {
            "<": TokenType.LT,
            ">": TokenType.GT,
            ":": TokenType.COLON,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            ",": TokenType.COMMA,
            ".": TokenType.DOT,
            "%": TokenType.PERCENT,
        }
        if ch in single:
            self._advance()
            self._emit(single[ch], ch, start)
            return

        raise LexError(
            f"Unexpected character {ch!r}",
            self._token_line,
            self._token_col,
            start,
        )

    # ------------------------------------------------------------------
    # Token-specific scanners
    # ------------------------------------------------------------------

    def _scan_line_comment(self, start: int) -> None:
        """Consume a ``//`` comment through the end of the line."""
        # Consume '//'
        self._advance()
        self._advance()
        text_start = self._pos
        while self._pos < len(self._source) and self._current() != "\n":
            self._advance()
        value = "//" + self._source[text_start : self._pos]
        self._emit(TokenType.COMMENT, value, start)

    def _scan_block_comment(self, start: int) -> None:
        """Consume a ``/* ... */`` block comment."""
        # Consume '/*'
        self._advance()
        self._advance()
        text_start = self._pos
        while self._pos < len(self._source):
            if self._current() == "*" and self._peek() == "/":
                value = "/*" + self._source[text_start : self._pos] + "*/"
                self._advance()  # *
                self._advance()  # /
                self._emit(TokenType.COMMENT, value, start)
                return
            self._advance()
        raise LexError(
            "Unterminated block comment",
            self._token_line,
            self._token_col,
            start,
        )

    def _scan_string(self, start: int) -> None:
        """Consume a double-quoted string literal with backslash escape support."""
        self._advance()  # opening "
        buf: list[str] = []
        while self._pos < len(self._source):
            ch = self._current()
            if ch == '"':
                self._advance()  # closing "
                self._emit(TokenType.STRING, "".join(buf), start)
                return
            if ch == "\\":
                self._advance()  # backslash
                esc = self._current()
                if esc in _ESCAPE_MAP:
                    buf.append(_ESCAPE_MAP[esc])
                    self._advance()
                else:
                    buf.append("\\")
                    buf.append(esc)
                    self._advance()
            elif ch == "\n":
                raise LexError(
                    "Unterminated string literal (newline in string)",
                    self._token_line,
                    self._token_col,
                    start,
                )
            else:
                buf.append(ch)
                self._advance()
        raise LexError(
            "Unterminated string literal (EOF)",
            self._token_line,
            self._token_col,
            start,
        )

    def _scan_number(self, start: int) -> None:
        """Consume an integer or float literal."""
        buf: list[str] = []
        while self._pos < len(self._source) and _DIGIT.match(self._current()):
            buf.append(self._advance())
        if self._current() == "." and _DIGIT.match(self._peek()):
            buf.append(self._advance())  # dot
            while self._pos < len(self._source) and _DIGIT.match(self._current()):
                buf.append(self._advance())
        self._emit(TokenType.NUMBER, "".join(buf), start)

    def _scan_ident_or_keyword(self, start: int) -> None:
        """Consume an identifier, then classify it as keyword or IDENT.

        Handles multi-word keywords that use underscores, such as
        ``must_not``, ``all_behaviors``, ``escalate_to_human``, etc.
        """
        buf: list[str] = []
        while self._pos < len(self._source) and _IDENT_CONT.match(self._current()):
            buf.append(self._advance())
        word = "".join(buf)
        token_type = KEYWORDS.get(word, TokenType.IDENT)

        # Special handling: 'none' in context of audit level — emit as IDENT
        # so the parser can interpret it; KEYWORDS maps it to AUDIT which
        # causes confusion. We re-map it here to keep the lexer dumb.
        # The parser handles 'none' as an audit-level value by checking value.
        if word == "none":
            token_type = TokenType.IDENT

        self._emit(token_type, word, start)


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


def tokenize(source: str) -> list[Token]:
    """Tokenize a BSL source string and return the complete token list.

    Parameters
    ----------
    source:
        BSL source text.

    Returns
    -------
    list[Token]
        All tokens including COMMENT and NEWLINE tokens, terminated by EOF.

    Raises
    ------
    LexError
        If the source contains invalid characters or unterminated literals.

    Example
    -------
    ::

        from bsl.lexer import tokenize
        tokens = tokenize('agent MyAgent { version: "1.0" }')
    """
    return Lexer(source).tokenize()
