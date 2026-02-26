"""Formal grammar rules for the Behavioral Specification Language.

This module documents the BSL grammar as EBNF-style string constants.
The grammar is implemented as a hand-written recursive-descent parser
(see ``bsl.parser``), but these constants serve as authoritative
reference documentation and are used by the formatter to understand
production ordering.

Grammar notation used here:
    ``::=``     production rule
    ``|``       alternation
    ``( )``     grouping
    ``[ ]``     optional (zero or one)
    ``{ }``     zero or more repetitions
    ``STRING``  terminal: double-quoted string literal
    ``NUMBER``  terminal: integer or float literal
    ``BOOL``    terminal: ``true`` or ``false``
    ``IDENT``   terminal: identifier (letter/underscore followed by word chars)
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------

GRAMMAR_ROOT = """
bsl_file ::= agent_spec EOF

agent_spec ::= 'agent' IDENT '{' agent_body '}'

agent_body ::=
    version_decl?
    model_decl?
    owner_decl?
    behavior_decl*
    invariant_decl*
    degradation_decl*
    composition_decl*
"""

# ---------------------------------------------------------------------------
# Metadata declarations
# ---------------------------------------------------------------------------

GRAMMAR_METADATA = """
version_decl ::= 'version' ':' STRING
model_decl   ::= 'model'   ':' STRING
owner_decl   ::= 'owner'   ':' STRING
"""

# ---------------------------------------------------------------------------
# Behavior
# ---------------------------------------------------------------------------

GRAMMAR_BEHAVIOR = """
behavior_decl ::= 'behavior' IDENT '{' behavior_body '}'

behavior_body ::=
    when_clause?
    confidence_clause?
    latency_clause?
    cost_clause?
    escalation_clause?
    audit_clause?
    must_clause*
    must_not_clause*
    should_clause*
    may_clause*

when_clause       ::= 'when' ':' expression
confidence_clause ::= 'confidence' ':' threshold_clause
latency_clause    ::= 'latency'    ':' threshold_clause
cost_clause       ::= 'cost'       ':' threshold_clause

escalation_clause ::= 'escalate_to_human' 'when' ':' expression
audit_clause      ::= 'audit'  ':' audit_level

audit_level ::= 'none' | 'basic' | 'full_trace'

must_clause     ::= 'must'     ':' expression
must_not_clause ::= 'must_not' ':' expression
should_clause   ::= 'should'   ':' expression ( NUMBER '%' 'of' 'cases' )?
may_clause      ::= 'may'      ':' expression
"""

# ---------------------------------------------------------------------------
# Threshold
# ---------------------------------------------------------------------------

GRAMMAR_THRESHOLD = """
threshold_clause ::= comparison_op NUMBER ( '%' )?

comparison_op ::= '<' | '>' | '<=' | '>=' | '==' | '!='
"""

# ---------------------------------------------------------------------------
# Invariant
# ---------------------------------------------------------------------------

GRAMMAR_INVARIANT = """
invariant_decl ::= 'invariant' IDENT '{' invariant_body '}'

invariant_body ::=
    applies_to_clause?
    severity_clause?
    must_clause*
    must_not_clause*

applies_to_clause ::= 'applies_to' ':' ( 'all_behaviors' | ident_list )
severity_clause   ::= 'severity'   ':' severity_level

severity_level ::= 'critical' | 'high' | 'medium' | 'low'

ident_list ::= '[' IDENT ( ',' IDENT )* ']'
"""

# ---------------------------------------------------------------------------
# Degradation
# ---------------------------------------------------------------------------

GRAMMAR_DEGRADATION = """
degradation_decl ::= 'degrades_to' IDENT 'when' ':' expression
"""

# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------

GRAMMAR_COMPOSITION = """
composition_decl ::= receives_decl | delegates_decl

receives_decl   ::= 'receives'    'from' IDENT
delegates_decl  ::= 'delegates_to' IDENT
"""

# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

GRAMMAR_EXPRESSION = """
expression ::= or_expr

or_expr  ::= and_expr  ( 'or'  and_expr  )*
and_expr ::= not_expr  ( 'and' not_expr  )*
not_expr ::= 'not' not_expr | comparison_expr

comparison_expr ::=
    temporal_expr
    ( ( '==' | '!=' | '<' | '>' | '<=' | '>=' ) temporal_expr )?

temporal_expr ::=
    member_expr ( ( 'before' | 'after' ) member_expr )?

member_expr ::=
    primary_expr ( 'contains' primary_expr )?

primary_expr ::=
    function_call
    | dot_access
    | IDENT
    | STRING
    | NUMBER
    | BOOL
    | '(' expression ')'
    | in_expr

function_call ::= IDENT '(' argument_list? ')'
argument_list ::= expression ( ',' expression )*

dot_access ::= IDENT ( '.' IDENT )+

in_expr ::= expression 'in' '[' expression_list ']'
expression_list ::= expression ( ',' expression )*
"""

# ---------------------------------------------------------------------------
# Full grammar as one string (for documentation / tooling consumers)
# ---------------------------------------------------------------------------

FULL_GRAMMAR: str = "\n".join([
    "# BSL Formal Grammar (EBNF-like notation)",
    "# ==========================================",
    "",
    "# Root",
    GRAMMAR_ROOT,
    "# Metadata",
    GRAMMAR_METADATA,
    "# Behavior",
    GRAMMAR_BEHAVIOR,
    "# Threshold",
    GRAMMAR_THRESHOLD,
    "# Invariant",
    GRAMMAR_INVARIANT,
    "# Degradation",
    GRAMMAR_DEGRADATION,
    "# Composition",
    GRAMMAR_COMPOSITION,
    "# Expressions",
    GRAMMAR_EXPRESSION,
])

# Production ordering used by the formatter to enforce canonical ordering
# of clauses within a behavior block.
BEHAVIOR_CLAUSE_ORDER: list[str] = [
    "when",
    "confidence",
    "latency",
    "cost",
    "audit",
    "escalate_to_human",
    "must",
    "must_not",
    "should",
    "may",
]

# Canonical ordering of clauses within an invariant block.
INVARIANT_CLAUSE_ORDER: list[str] = [
    "applies_to",
    "severity",
    "must",
    "must_not",
]

# Canonical ordering of agent-level metadata fields.
AGENT_METADATA_ORDER: list[str] = [
    "version",
    "model",
    "owner",
]
