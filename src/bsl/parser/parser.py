"""BSL Recursive-Descent Parser.

Converts a flat list of ``Token`` objects into an ``AgentSpec`` AST.

The parser skips COMMENT and NEWLINE tokens transparently, so the grammar
rules are stated in terms of meaningful tokens only.

Error recovery
--------------
When an unexpected token is encountered the parser records a ``ParseError``
and synchronizes by consuming tokens until a ``}`` or ``EOF`` is found,
then attempts to continue with the next top-level declaration.  This
means a single run can surface multiple independent errors.

If the source is fatally malformed the parser raises ``ParseErrorCollection``
after exhausting recovery attempts.

Expression parsing follows standard precedence rules via the Pratt / recursive
descent approach:

    or > and > not > comparison > temporal > member > primary
"""
from __future__ import annotations

from bsl.ast.nodes import (
    AfterExpr,
    AgentSpec,
    AppliesTo,
    AuditLevel,
    Behavior,
    BeforeExpr,
    BinOp,
    BinaryOpExpr,
    BoolLit,
    Composition,
    Constraint,
    ContainsExpr,
    Degradation,
    Delegates,
    DotAccess,
    EscalationClause,
    Expression,
    FunctionCall,
    Identifier,
    InListExpr,
    Invariant,
    NumberLit,
    Receives,
    Severity,
    ShouldConstraint,
    Span,
    StringLit,
    ThresholdClause,
    UnaryOpExpr,
    UnaryOpKind,
)
from bsl.grammar.tokens import Token, TokenType
from bsl.lexer.lexer import tokenize
from bsl.parser.errors import ParseError, ParseErrorCollection, RecoveryStrategy

# ---------------------------------------------------------------------------
# Internal sentinel
# ---------------------------------------------------------------------------

_SYNC_TOKENS = frozenset({TokenType.RBRACE, TokenType.EOF})
_COMPARISON_OPS = frozenset({TokenType.EQ, TokenType.NEQ, TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE})
_SEVERITY_MAP: dict[str, Severity] = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
}
_AUDIT_MAP: dict[str, AuditLevel] = {
    "none": AuditLevel.NONE,
    "basic": AuditLevel.BASIC,
    "full_trace": AuditLevel.FULL_TRACE,
}
_BINOP_MAP: dict[TokenType, BinOp] = {
    TokenType.EQ: BinOp.EQ,
    TokenType.NEQ: BinOp.NEQ,
    TokenType.LT: BinOp.LT,
    TokenType.GT: BinOp.GT,
    TokenType.LTE: BinOp.LTE,
    TokenType.GTE: BinOp.GTE,
}


class Parser:
    """Recursive descent parser that produces an ``AgentSpec`` from tokens.

    Parameters
    ----------
    tokens:
        The flat token list produced by the lexer.  Must include the
        terminal ``EOF`` token.
    """

    def __init__(self, tokens: list[Token]) -> None:
        # Filter out COMMENT and NEWLINE tokens — the grammar ignores them.
        self._tokens: list[Token] = [
            t for t in tokens if t.type not in (TokenType.COMMENT, TokenType.NEWLINE)
        ]
        self._pos: int = 0
        self._errors: ParseErrorCollection = ParseErrorCollection()

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def _current(self) -> Token:
        """Return the current token without consuming it."""
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return self._tokens[-1]  # EOF

    def _peek(self, offset: int = 1) -> Token:
        """Return the token ``offset`` positions ahead without consuming."""
        idx = self._pos + offset
        if idx < len(self._tokens):
            return self._tokens[idx]
        return self._tokens[-1]

    def _advance(self) -> Token:
        """Consume and return the current token."""
        tok = self._current()
        if tok.type != TokenType.EOF:
            self._pos += 1
        return tok

    def _check(self, *types: TokenType) -> bool:
        """Return True if the current token matches any of the given types."""
        return self._current().type in types

    def _match(self, *types: TokenType) -> Token | None:
        """Consume and return the current token if it matches; else None."""
        if self._check(*types):
            return self._advance()
        return None

    def _expect(self, token_type: TokenType, message: str | None = None) -> Token:
        """Consume the current token if it matches, else record an error.

        Returns the token even on mismatch (for error recovery), using
        a synthetic token with an empty value so subsequent parsing can
        continue.
        """
        tok = self._current()
        if tok.type == token_type:
            return self._advance()
        msg = message or f"Expected {token_type.name}"
        self._record_error(msg, (token_type,), RecoveryStrategy.INSERT_MISSING)
        # Return synthetic token so callers don't need to handle None
        return Token(
            type=token_type,
            value="",
            line=tok.line,
            col=tok.col,
            offset=tok.offset,
        )

    def _span_from(self, tok: Token) -> Span:
        """Build a ``Span`` anchored at the given token."""
        return Span(
            start=tok.offset,
            end=tok.offset + len(tok.value),
            line=tok.line,
            col=tok.col,
        )

    def _span_between(self, start_tok: Token, end_tok: Token) -> Span:
        """Build a ``Span`` covering from ``start_tok`` to ``end_tok``."""
        return Span(
            start=start_tok.offset,
            end=end_tok.offset + len(end_tok.value),
            line=start_tok.line,
            col=start_tok.col,
        )

    def _record_error(
        self,
        message: str,
        expected: tuple[TokenType, ...],
        recovery: RecoveryStrategy,
    ) -> None:
        tok = self._current()
        span = self._span_from(tok)
        self._errors.add(
            ParseError(
                message=message,
                span=span,
                expected=expected,
                found=tok,
                recovery=recovery,
            )
        )

    def _synchronize(self) -> None:
        """Skip tokens until we find a synchronization point."""
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            self._advance()

    # ------------------------------------------------------------------
    # Top-level parse
    # ------------------------------------------------------------------

    def parse(self) -> AgentSpec:
        """Parse the token stream and return the root ``AgentSpec``.

        Raises
        ------
        ParseErrorCollection
            If any errors were recorded during parsing.
        """
        spec = self._parse_agent()
        self._expect(TokenType.EOF, "Expected end of file after agent block")
        if self._errors.has_errors:
            raise self._errors
        return spec

    def _parse_agent(self) -> AgentSpec:
        """Parse: ``agent IDENT '{' agent_body '}'``"""
        start_tok = self._expect(TokenType.AGENT, "Expected 'agent' keyword")
        name_tok = self._expect(TokenType.IDENT, "Expected agent name after 'agent'")
        self._expect(TokenType.LBRACE, "Expected '{' after agent name")

        version: str | None = None
        model: str | None = None
        owner: str | None = None
        behaviors: list[Behavior] = []
        invariants: list[Invariant] = []
        degradations: list[Degradation] = []
        compositions: list[Composition] = []

        while not self._check(TokenType.RBRACE, TokenType.EOF):
            tok = self._current()
            try:
                if tok.type == TokenType.VERSION:
                    version = self._parse_string_field(TokenType.VERSION)
                elif tok.type == TokenType.MODEL:
                    model = self._parse_string_field(TokenType.MODEL)
                elif tok.type == TokenType.OWNER:
                    owner = self._parse_string_field(TokenType.OWNER)
                elif tok.type == TokenType.BEHAVIOR:
                    behaviors.append(self._parse_behavior())
                elif tok.type == TokenType.INVARIANT:
                    invariants.append(self._parse_invariant())
                elif tok.type == TokenType.DEGRADES_TO:
                    degradations.append(self._parse_degradation())
                elif tok.type == TokenType.RECEIVES:
                    compositions.append(self._parse_receives())
                elif tok.type == TokenType.DELEGATES_TO:
                    compositions.append(self._parse_delegates())
                else:
                    self._record_error(
                        f"Unexpected token {tok.value!r} in agent body",
                        (TokenType.BEHAVIOR, TokenType.INVARIANT, TokenType.RBRACE),
                        RecoveryStrategy.SKIP_TOKEN,
                    )
                    self._advance()
            except ParseError:
                self._synchronize()

        end_tok = self._expect(TokenType.RBRACE, "Expected '}' to close agent block")
        span = self._span_between(start_tok, end_tok)
        return AgentSpec(
            name=name_tok.value,
            version=version,
            model=model,
            owner=owner,
            behaviors=tuple(behaviors),
            invariants=tuple(invariants),
            degradations=tuple(degradations),
            compositions=tuple(compositions),
            span=span,
        )

    # ------------------------------------------------------------------
    # Simple metadata field parsers
    # ------------------------------------------------------------------

    def _parse_string_field(self, keyword_type: TokenType) -> str:
        """Parse: ``KEYWORD ':' STRING``  → the string value."""
        self._advance()  # consume keyword
        self._expect(TokenType.COLON, f"Expected ':' after {keyword_type.name.lower()}")
        tok = self._expect(TokenType.STRING, f"Expected string value for {keyword_type.name.lower()}")
        return tok.value

    # ------------------------------------------------------------------
    # Behavior parser
    # ------------------------------------------------------------------

    def _parse_behavior(self) -> Behavior:
        """Parse a ``behavior IDENT '{' ... '}'`` block."""
        start_tok = self._advance()  # consume 'behavior'
        name_tok = self._expect(TokenType.IDENT, "Expected behavior name")
        self._expect(TokenType.LBRACE, "Expected '{' after behavior name")

        when_clause: Expression | None = None
        confidence: ThresholdClause | None = None
        latency: ThresholdClause | None = None
        cost: ThresholdClause | None = None
        escalation: EscalationClause | None = None
        audit: AuditLevel = AuditLevel.NONE
        must_constraints: list[Constraint] = []
        must_not_constraints: list[Constraint] = []
        should_constraints: list[ShouldConstraint] = []
        may_constraints: list[Constraint] = []

        while not self._check(TokenType.RBRACE, TokenType.EOF):
            tok = self._current()
            try:
                if tok.type == TokenType.WHEN:
                    when_clause = self._parse_when_clause()
                elif tok.type == TokenType.CONFIDENCE:
                    confidence = self._parse_threshold_field(TokenType.CONFIDENCE)
                elif tok.type == TokenType.LATENCY:
                    latency = self._parse_threshold_field(TokenType.LATENCY)
                elif tok.type == TokenType.COST:
                    cost = self._parse_threshold_field(TokenType.COST)
                elif tok.type == TokenType.ESCALATE_TO_HUMAN:
                    escalation = self._parse_escalation()
                elif tok.type == TokenType.AUDIT:
                    audit = self._parse_audit_level()
                elif tok.type == TokenType.MUST:
                    must_constraints.append(self._parse_constraint(TokenType.MUST))
                elif tok.type == TokenType.MUST_NOT:
                    must_not_constraints.append(self._parse_constraint(TokenType.MUST_NOT))
                elif tok.type == TokenType.SHOULD:
                    should_constraints.append(self._parse_should_constraint())
                elif tok.type == TokenType.MAY:
                    may_constraints.append(self._parse_constraint(TokenType.MAY))
                else:
                    self._record_error(
                        f"Unexpected token {tok.value!r} in behavior body",
                        (TokenType.MUST, TokenType.MUST_NOT, TokenType.SHOULD, TokenType.RBRACE),
                        RecoveryStrategy.SKIP_TOKEN,
                    )
                    self._advance()
            except ParseError:
                self._synchronize()

        end_tok = self._expect(TokenType.RBRACE, "Expected '}' to close behavior block")
        span = self._span_between(start_tok, end_tok)
        return Behavior(
            name=name_tok.value,
            when_clause=when_clause,
            must_constraints=tuple(must_constraints),
            must_not_constraints=tuple(must_not_constraints),
            should_constraints=tuple(should_constraints),
            may_constraints=tuple(may_constraints),
            confidence=confidence,
            latency=latency,
            cost=cost,
            escalation=escalation,
            audit=audit,
            span=span,
        )

    def _parse_when_clause(self) -> Expression:
        """Parse: ``when ':' expression``"""
        self._advance()  # consume 'when'
        self._expect(TokenType.COLON, "Expected ':' after 'when'")
        return self._parse_expression()

    def _parse_threshold_field(self, keyword_type: TokenType) -> ThresholdClause:
        """Parse: ``KEYWORD ':' comparison_op NUMBER ['%']``"""
        start_tok = self._advance()  # consume keyword
        self._expect(TokenType.COLON, f"Expected ':' after {keyword_type.name.lower()}")
        return self._parse_threshold_clause(start_tok)

    def _parse_threshold_clause(self, start_tok: Token) -> ThresholdClause:
        """Parse: ``comparison_op NUMBER ['%']``"""
        tok = self._current()
        if tok.type not in _COMPARISON_OPS:
            self._record_error(
                "Expected comparison operator (<, >, <=, >=, ==, !=)",
                tuple(_COMPARISON_OPS),
                RecoveryStrategy.INSERT_MISSING,
            )
            op = "<"
        else:
            op = tok.value
            self._advance()

        num_tok = self._expect(TokenType.NUMBER, "Expected numeric threshold value")
        try:
            value = float(num_tok.value)
        except ValueError:
            value = 0.0

        is_percentage = False
        end_tok = num_tok
        if self._check(TokenType.PERCENT):
            end_tok = self._advance()
            is_percentage = True

        span = self._span_between(start_tok, end_tok)
        return ThresholdClause(operator=op, value=value, is_percentage=is_percentage, span=span)

    def _parse_escalation(self) -> EscalationClause:
        """Parse: ``escalate_to_human when ':' expression``"""
        start_tok = self._advance()  # consume 'escalate_to_human'
        self._expect(TokenType.WHEN, "Expected 'when' after 'escalate_to_human'")
        self._expect(TokenType.COLON, "Expected ':' after 'when'")
        expr = self._parse_expression()
        span = Span(
            start=start_tok.offset,
            end=expr.span.end,
            line=start_tok.line,
            col=start_tok.col,
        )
        return EscalationClause(condition=expr, span=span)

    def _parse_audit_level(self) -> AuditLevel:
        """Parse: ``audit ':' ('none' | 'basic' | 'full_trace')``"""
        self._advance()  # consume 'audit'
        self._expect(TokenType.COLON, "Expected ':' after 'audit'")
        tok = self._current()
        level_str = tok.value.lower()
        if level_str in _AUDIT_MAP:
            self._advance()
            return _AUDIT_MAP[level_str]
        # Accept IDENT tokens with audit level values
        self._record_error(
            f"Expected audit level (none, basic, full_trace), got {tok.value!r}",
            (TokenType.IDENT,),
            RecoveryStrategy.INSERT_MISSING,
        )
        return AuditLevel.NONE

    def _parse_constraint(self, keyword_type: TokenType) -> Constraint:
        """Parse: ``KEYWORD ':' expression``"""
        start_tok = self._advance()  # consume keyword
        self._expect(TokenType.COLON, f"Expected ':' after '{keyword_type.name.lower()}'")
        expr = self._parse_expression()
        span = Span(
            start=start_tok.offset,
            end=expr.span.end,
            line=start_tok.line,
            col=start_tok.col,
        )
        return Constraint(expression=expr, span=span)

    def _parse_should_constraint(self) -> ShouldConstraint:
        """Parse: ``should ':' expression [NUMBER '%' 'of' 'cases']``"""
        start_tok = self._advance()  # consume 'should'
        self._expect(TokenType.COLON, "Expected ':' after 'should'")
        expr = self._parse_expression()
        percentage: float | None = None

        # Check for optional percentage qualifier: NUMBER '%' 'of' 'cases'
        if self._check(TokenType.NUMBER):
            num_tok = self._advance()
            if self._check(TokenType.PERCENT):
                self._advance()  # %
                if self._check(TokenType.OF):
                    self._advance()  # of
                    if self._check(TokenType.CASES):
                        self._advance()  # cases
                try:
                    percentage = float(num_tok.value)
                except ValueError:
                    percentage = None

        span = Span(start=start_tok.offset, end=expr.span.end, line=start_tok.line, col=start_tok.col)
        return ShouldConstraint(expression=expr, percentage=percentage, span=span)

    # ------------------------------------------------------------------
    # Invariant parser
    # ------------------------------------------------------------------

    def _parse_invariant(self) -> Invariant:
        """Parse: ``invariant IDENT '{' invariant_body '}'``"""
        start_tok = self._advance()  # consume 'invariant'
        name_tok = self._expect(TokenType.IDENT, "Expected invariant name")
        self._expect(TokenType.LBRACE, "Expected '{' after invariant name")

        applies_to: AppliesTo = AppliesTo.ALL_BEHAVIORS
        named_behaviors: list[str] = []
        severity: Severity = Severity.HIGH
        constraints: list[Constraint] = []
        prohibitions: list[Constraint] = []

        while not self._check(TokenType.RBRACE, TokenType.EOF):
            tok = self._current()
            try:
                if tok.type == TokenType.APPLIES_TO:
                    applies_to, named_behaviors = self._parse_applies_to()
                elif tok.type == TokenType.SEVERITY:
                    severity = self._parse_severity()
                elif tok.type == TokenType.MUST:
                    constraints.append(self._parse_constraint(TokenType.MUST))
                elif tok.type == TokenType.MUST_NOT:
                    prohibitions.append(self._parse_constraint(TokenType.MUST_NOT))
                else:
                    self._record_error(
                        f"Unexpected token {tok.value!r} in invariant body",
                        (TokenType.MUST, TokenType.MUST_NOT, TokenType.RBRACE),
                        RecoveryStrategy.SKIP_TOKEN,
                    )
                    self._advance()
            except ParseError:
                self._synchronize()

        end_tok = self._expect(TokenType.RBRACE, "Expected '}' to close invariant block")
        span = self._span_between(start_tok, end_tok)
        return Invariant(
            name=name_tok.value,
            constraints=tuple(constraints),
            prohibitions=tuple(prohibitions),
            applies_to=applies_to,
            named_behaviors=tuple(named_behaviors),
            severity=severity,
            span=span,
        )

    def _parse_applies_to(self) -> tuple[AppliesTo, list[str]]:
        """Parse: ``applies_to ':' ('all_behaviors' | '[' IDENT* ']')``"""
        self._advance()  # consume 'applies_to'
        self._expect(TokenType.COLON, "Expected ':' after 'applies_to'")
        if self._check(TokenType.ALL_BEHAVIORS):
            self._advance()
            return AppliesTo.ALL_BEHAVIORS, []
        # Named list: '[' IDENT (',' IDENT)* ']'
        self._expect(TokenType.LBRACKET, "Expected '[' or 'all_behaviors' after 'applies_to:'")
        names: list[str] = []
        while not self._check(TokenType.RBRACKET, TokenType.EOF):
            name_tok = self._expect(TokenType.IDENT, "Expected behavior name in applies_to list")
            names.append(name_tok.value)
            if not self._match(TokenType.COMMA):
                break
        self._expect(TokenType.RBRACKET, "Expected ']' to close applies_to list")
        return AppliesTo.NAMED, names

    def _parse_severity(self) -> Severity:
        """Parse: ``severity ':' ('critical' | 'high' | 'medium' | 'low')``"""
        self._advance()  # consume 'severity'
        self._expect(TokenType.COLON, "Expected ':' after 'severity'")
        tok = self._current()
        level_str = tok.value.lower()
        if level_str in _SEVERITY_MAP:
            self._advance()
            return _SEVERITY_MAP[level_str]
        self._record_error(
            f"Expected severity level (critical, high, medium, low), got {tok.value!r}",
            (TokenType.IDENT,),
            RecoveryStrategy.INSERT_MISSING,
        )
        return Severity.HIGH

    # ------------------------------------------------------------------
    # Degradation and composition parsers
    # ------------------------------------------------------------------

    def _parse_degradation(self) -> Degradation:
        """Parse: ``degrades_to IDENT when ':' expression``"""
        start_tok = self._advance()  # consume 'degrades_to'
        fallback_tok = self._expect(TokenType.IDENT, "Expected fallback agent/behavior name")
        self._expect(TokenType.WHEN, "Expected 'when' after fallback name in degrades_to")
        self._expect(TokenType.COLON, "Expected ':' after 'when'")
        expr = self._parse_expression()
        span = Span(
            start=start_tok.offset,
            end=expr.span.end,
            line=start_tok.line,
            col=start_tok.col,
        )
        return Degradation(fallback=fallback_tok.value, condition=expr, span=span)

    def _parse_receives(self) -> Receives:
        """Parse: ``receives from IDENT``"""
        start_tok = self._advance()  # consume 'receives'
        # Consume optional 'from' keyword (parsed as IDENT since 'from' is not a keyword)
        if self._check(TokenType.IDENT) and self._current().value == "from":
            self._advance()
        source_tok = self._expect(TokenType.IDENT, "Expected source agent name after 'receives from'")
        span = self._span_between(start_tok, source_tok)
        return Receives(source_agent=source_tok.value, span=span)

    def _parse_delegates(self) -> Delegates:
        """Parse: ``delegates_to IDENT``"""
        start_tok = self._advance()  # consume 'delegates_to'
        target_tok = self._expect(TokenType.IDENT, "Expected target agent name after 'delegates_to'")
        span = self._span_between(start_tok, target_tok)
        return Delegates(target_agent=target_tok.value, span=span)

    # ------------------------------------------------------------------
    # Expression parsing (precedence climbing)
    # ------------------------------------------------------------------

    def _parse_expression(self) -> Expression:
        """Entry point for expression parsing (lowest precedence)."""
        return self._parse_or()

    def _parse_or(self) -> Expression:
        """Parse: ``and_expr ('or' and_expr)*``"""
        left = self._parse_and()
        while self._check(TokenType.OR):
            self._advance()
            right = self._parse_and()
            span = Span(
                start=left.span.start,
                end=right.span.end,
                line=left.span.line,
                col=left.span.col,
            )
            left = BinaryOpExpr(op=BinOp.OR, left=left, right=right, span=span)
        return left

    def _parse_and(self) -> Expression:
        """Parse: ``not_expr ('and' not_expr)*``"""
        left = self._parse_not()
        while self._check(TokenType.AND):
            self._advance()
            right = self._parse_not()
            span = Span(
                start=left.span.start,
                end=right.span.end,
                line=left.span.line,
                col=left.span.col,
            )
            left = BinaryOpExpr(op=BinOp.AND, left=left, right=right, span=span)
        return left

    def _parse_not(self) -> Expression:
        """Parse: ``'not' not_expr | comparison_expr``"""
        if self._check(TokenType.NOT):
            op_tok = self._advance()
            operand = self._parse_not()
            span = Span(
                start=op_tok.offset,
                end=operand.span.end,
                line=op_tok.line,
                col=op_tok.col,
            )
            return UnaryOpExpr(op=UnaryOpKind.NOT, operand=operand, span=span)
        return self._parse_comparison()

    def _parse_comparison(self) -> Expression:
        """Parse: ``temporal_expr (comparison_op temporal_expr)?``"""
        left = self._parse_temporal()
        if self._current().type in _BINOP_MAP:
            op = _BINOP_MAP[self._current().type]
            self._advance()
            right = self._parse_temporal()
            span = Span(
                start=left.span.start,
                end=right.span.end,
                line=left.span.line,
                col=left.span.col,
            )
            return BinaryOpExpr(op=op, left=left, right=right, span=span)
        return left

    def _parse_temporal(self) -> Expression:
        """Parse: ``member_expr ('before'|'after' member_expr)?``"""
        left = self._parse_member()
        if self._check(TokenType.BEFORE):
            self._advance()
            right = self._parse_member()
            span = Span(start=left.span.start, end=right.span.end, line=left.span.line, col=left.span.col)
            return BeforeExpr(left=left, right=right, span=span)
        if self._check(TokenType.AFTER):
            self._advance()
            right = self._parse_member()
            span = Span(start=left.span.start, end=right.span.end, line=left.span.line, col=left.span.col)
            return AfterExpr(left=left, right=right, span=span)
        return left

    def _parse_member(self) -> Expression:
        """Parse: ``primary ('contains' primary)?``"""
        left = self._parse_primary()
        if self._check(TokenType.CONTAINS):
            self._advance()
            right = self._parse_primary()
            span = Span(start=left.span.start, end=right.span.end, line=left.span.line, col=left.span.col)
            return ContainsExpr(subject=left, value=right, span=span)
        if self._check(TokenType.IN):
            self._advance()
            self._expect(TokenType.LBRACKET, "Expected '[' after 'in'")
            items: list[Expression] = []
            while not self._check(TokenType.RBRACKET, TokenType.EOF):
                items.append(self._parse_expression())
                if not self._match(TokenType.COMMA):
                    break
            end_tok = self._expect(TokenType.RBRACKET, "Expected ']' to close 'in' list")
            span = Span(start=left.span.start, end=end_tok.offset + 1, line=left.span.line, col=left.span.col)
            return InListExpr(subject=left, items=tuple(items), span=span)
        return left

    def _parse_primary(self) -> Expression:
        """Parse a primary expression: literal, identifier, dot-access, function call, or grouped."""
        tok = self._current()

        # Parenthesized expression
        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN, "Expected ')' to close grouped expression")
            return expr

        # String literal
        if tok.type == TokenType.STRING:
            self._advance()
            span = self._span_from(tok)
            return StringLit(value=tok.value, span=span)

        # Number literal
        if tok.type == TokenType.NUMBER:
            self._advance()
            span = self._span_from(tok)
            return NumberLit(value=float(tok.value), span=span)

        # Bool literal
        if tok.type == TokenType.BOOL:
            self._advance()
            span = self._span_from(tok)
            return BoolLit(value=tok.value.lower() == "true", span=span)

        # Identifier, dot-access, or function call.
        # Exclude pure operator keywords that should have been consumed at higher
        # parse levels — if they reach here, the expression is malformed.
        _operator_keyword_types = frozenset({
            TokenType.AND, TokenType.OR, TokenType.NOT,
            TokenType.BEFORE, TokenType.AFTER, TokenType.CONTAINS,
            TokenType.IN, TokenType.OF, TokenType.CASES,
        })
        if (tok.type == TokenType.IDENT or tok.is_keyword) and tok.type not in _operator_keyword_types:
            name_tok = self._advance()
            start_span = self._span_from(name_tok)

            # Function call: IDENT '(' args ')'
            if self._check(TokenType.LPAREN):
                self._advance()
                args: list[Expression] = []
                while not self._check(TokenType.RPAREN, TokenType.EOF):
                    args.append(self._parse_expression())
                    if not self._match(TokenType.COMMA):
                        break
                end_tok = self._expect(TokenType.RPAREN, "Expected ')' to close function call")
                span = self._span_between(name_tok, end_tok)
                return FunctionCall(name=name_tok.value, arguments=tuple(args), span=span)

            # Dot access: IDENT ('.' IDENT)+
            # Note: after '.', accept IDENT or any keyword token as a member name,
            # since BSL allows attribute names that coincide with keywords
            # e.g. response.model, request.before, etc.
            if self._check(TokenType.DOT):
                parts: list[str] = [name_tok.value]
                last_tok = name_tok
                while self._check(TokenType.DOT):
                    self._advance()  # consume '.'
                    part_tok = self._current()
                    if part_tok.type == TokenType.IDENT or part_tok.is_keyword:
                        self._advance()
                        parts.append(part_tok.value)
                        last_tok = part_tok
                    else:
                        self._record_error(
                            "Expected identifier after '.'",
                            (TokenType.IDENT,),
                            RecoveryStrategy.INSERT_MISSING,
                        )
                        break
                span = self._span_between(name_tok, last_tok)
                return DotAccess(parts=tuple(parts), span=span)

            return Identifier(name=name_tok.value, span=start_span)

        # Fallback: emit error and return a synthetic identifier
        self._record_error(
            f"Expected expression, got {tok.type.name} {tok.value!r}",
            (TokenType.IDENT, TokenType.STRING, TokenType.NUMBER),
            RecoveryStrategy.SKIP_TOKEN,
        )
        self._advance()
        span = self._span_from(tok)
        return Identifier(name="<error>", span=span)


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


def parse(source: str) -> AgentSpec:
    """Parse a BSL source string and return the root ``AgentSpec``.

    Parameters
    ----------
    source:
        Complete BSL source text.

    Returns
    -------
    AgentSpec
        The parsed agent specification.

    Raises
    ------
    LexError
        If the source contains invalid characters or unterminated literals.
    ParseErrorCollection
        If the source contains syntactic errors.

    Example
    -------
    ::

        from bsl.parser import parse
        spec = parse('''
            agent GreetingAgent {
              version: "1.0"
              behavior greet {
                must: response contains "Hello"
              }
            }
        ''')
    """
    tokens = tokenize(source)
    return Parser(tokens).parse()
