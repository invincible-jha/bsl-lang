"""AST node definitions for the Behavioral Specification Language.

Every node produced by the BSL parser is a frozen dataclass so that
AST trees are immutable and hashable.  The ``Expression`` union type
covers all expression variants; downstream code should use
``isinstance`` checks or the ``ExpressionKind`` helper to dispatch.

All nodes carry a ``Span`` that records their source location, enabling
precise error messages in the validator and linter.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Union


# ---------------------------------------------------------------------------
# Source location
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Span:
    """Half-open byte range ``[start, end)`` within the source text.

    Parameters
    ----------
    start:
        0-based byte offset of the first character.
    end:
        0-based byte offset *past* the last character.
    line:
        1-based line number of the first character.
    col:
        1-based column number of the first character.
    """

    start: int
    end: int
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Span({self.line}:{self.col})"

    @classmethod
    def unknown(cls) -> "Span":
        """Return a sentinel span used when position info is unavailable."""
        return cls(start=0, end=0, line=0, col=0)

    def merge(self, other: "Span") -> "Span":
        """Return a span that covers both ``self`` and ``other``."""
        return Span(
            start=min(self.start, other.start),
            end=max(self.end, other.end),
            line=min(self.line, other.line),
            col=self.col if self.line <= other.line else other.col,
        )


# ---------------------------------------------------------------------------
# Enums shared across node types
# ---------------------------------------------------------------------------


class AppliesTo(Enum):
    """Scope of an invariant: all behaviors or a named subset."""

    ALL_BEHAVIORS = auto()
    NAMED = auto()


class Severity(Enum):
    """Severity level for an invariant violation."""

    CRITICAL = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()


class AuditLevel(Enum):
    """Audit trace detail level for a behavior."""

    NONE = auto()
    BASIC = auto()
    FULL_TRACE = auto()


class BinOp(Enum):
    """Binary operator kinds used in expressions."""

    AND = auto()
    OR = auto()
    EQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()
    BEFORE = auto()
    AFTER = auto()
    CONTAINS = auto()
    IN = auto()


class UnaryOpKind(Enum):
    """Unary operator kinds."""

    NOT = auto()


# ---------------------------------------------------------------------------
# Literal sub-types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StringLit:
    """A double-quoted string literal value."""

    value: str
    span: Span


@dataclass(frozen=True, slots=True)
class NumberLit:
    """An integer or floating-point literal value."""

    value: float
    span: Span


@dataclass(frozen=True, slots=True)
class BoolLit:
    """A boolean literal (``true`` or ``false``)."""

    value: bool
    span: Span


Literal = Union[StringLit, NumberLit, BoolLit]

# ---------------------------------------------------------------------------
# Expression sub-types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Identifier:
    """A bare identifier reference, e.g. ``response``."""

    name: str
    span: Span


@dataclass(frozen=True, slots=True)
class DotAccess:
    """A dotted member access, e.g. ``response.status``."""

    parts: tuple[str, ...]
    span: Span

    @property
    def head(self) -> str:
        """Return the leftmost name component."""
        return self.parts[0]

    @property
    def tail(self) -> tuple[str, ...]:
        """Return all components after the head."""
        return self.parts[1:]


# Forward reference — BinaryOp and UnaryOp are recursive.
Expression = Union[
    "Identifier",
    "DotAccess",
    "Literal",
    "BinaryOpExpr",
    "UnaryOpExpr",
    "FunctionCall",
    "ContainsExpr",
    "InListExpr",
    "BeforeExpr",
    "AfterExpr",
]


@dataclass(frozen=True, slots=True)
class BinaryOpExpr:
    """A binary operator expression, e.g. ``a == b`` or ``x and y``."""

    op: BinOp
    left: "Expression"
    right: "Expression"
    span: Span


@dataclass(frozen=True, slots=True)
class UnaryOpExpr:
    """A unary operator expression, e.g. ``not flagged``."""

    op: UnaryOpKind
    operand: "Expression"
    span: Span


@dataclass(frozen=True, slots=True)
class FunctionCall:
    """A function-call expression, e.g. ``len(items)``."""

    name: str
    arguments: tuple["Expression", ...]
    span: Span


@dataclass(frozen=True, slots=True)
class ContainsExpr:
    """A ``contains`` membership test, e.g. ``response contains "error"``."""

    subject: "Expression"
    value: "Expression"
    span: Span


@dataclass(frozen=True, slots=True)
class InListExpr:
    """An ``in [...]`` membership test, e.g. ``status in [200, 201]``."""

    subject: "Expression"
    items: tuple["Expression", ...]
    span: Span


@dataclass(frozen=True, slots=True)
class BeforeExpr:
    """A temporal ordering expression ``a before b``."""

    left: "Expression"
    right: "Expression"
    span: Span


@dataclass(frozen=True, slots=True)
class AfterExpr:
    """A temporal ordering expression ``a after b``."""

    left: "Expression"
    right: "Expression"
    span: Span


# ---------------------------------------------------------------------------
# Constraint nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Constraint:
    """A ``must``, ``must_not``, or ``may`` constraint wrapping an expression."""

    expression: Expression
    span: Span


@dataclass(frozen=True, slots=True)
class ShouldConstraint:
    """A ``should`` constraint with an optional percentage-of-cases qualifier.

    Parameters
    ----------
    expression:
        The constrained expression.
    percentage:
        If not ``None``, the ``should`` clause applies in at least this
        percentage of cases (0–100).
    """

    expression: Expression
    percentage: float | None
    span: Span


# ---------------------------------------------------------------------------
# Threshold and escalation clauses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ThresholdClause:
    """A threshold specification, e.g. ``< 500`` or ``>= 95%``.

    Parameters
    ----------
    operator:
        One of ``<``, ``>``, ``<=``, ``>=``, ``==``, ``!=``.
    value:
        The numeric threshold value.
    is_percentage:
        Whether the value is expressed as a percentage.
    """

    operator: str
    value: float
    is_percentage: bool
    span: Span


@dataclass(frozen=True, slots=True)
class EscalationClause:
    """An ``escalate_to_human when`` clause."""

    condition: Expression
    span: Span


# ---------------------------------------------------------------------------
# Behavior node
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Behavior:
    """A named behavior block within an agent specification.

    Parameters
    ----------
    name:
        The identifier for this behavior.
    when_clause:
        Optional precondition expression.
    must_constraints:
        Hard constraints that must always hold.
    must_not_constraints:
        Hard prohibitions that must never hold.
    should_constraints:
        Soft constraints with optional percentage-of-cases qualifier.
    may_constraints:
        Permitted (but not required) actions.
    confidence:
        Optional minimum confidence threshold.
    latency:
        Optional maximum latency threshold.
    cost:
        Optional cost threshold.
    escalation:
        Optional escalation-to-human clause.
    audit:
        Audit level for this behavior.
    span:
        Source location.
    """

    name: str
    when_clause: Expression | None
    must_constraints: tuple[Constraint, ...]
    must_not_constraints: tuple[Constraint, ...]
    should_constraints: tuple[ShouldConstraint, ...]
    may_constraints: tuple[Constraint, ...]
    confidence: ThresholdClause | None
    latency: ThresholdClause | None
    cost: ThresholdClause | None
    escalation: EscalationClause | None
    audit: AuditLevel
    span: Span


# ---------------------------------------------------------------------------
# Invariant node
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Invariant:
    """A named invariant block that applies across behaviors.

    Parameters
    ----------
    name:
        The identifier for this invariant.
    constraints:
        Expressions that must hold.
    prohibitions:
        Expressions that must not hold.
    applies_to:
        Scope selector — ``ALL_BEHAVIORS`` or ``NAMED``.
    named_behaviors:
        When ``applies_to`` is ``NAMED``, the list of behavior names
        this invariant covers.
    severity:
        How serious a violation of this invariant is.
    span:
        Source location.
    """

    name: str
    constraints: tuple[Constraint, ...]
    prohibitions: tuple[Constraint, ...]
    applies_to: AppliesTo
    named_behaviors: tuple[str, ...]
    severity: Severity
    span: Span


# ---------------------------------------------------------------------------
# Degradation and composition nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Degradation:
    """A ``degrades_to`` fallback specification.

    Parameters
    ----------
    fallback:
        The name of the fallback behavior or agent.
    condition:
        The condition under which degradation is triggered.
    span:
        Source location.
    """

    fallback: str
    condition: Expression
    span: Span


@dataclass(frozen=True, slots=True)
class Receives:
    """A ``receives from`` composition clause — this agent receives input from another."""

    source_agent: str
    span: Span


@dataclass(frozen=True, slots=True)
class Delegates:
    """A ``delegates_to`` composition clause — this agent delegates to another."""

    target_agent: str
    span: Span


Composition = Union[Receives, Delegates]


# ---------------------------------------------------------------------------
# Top-level agent specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentSpec:
    """The root AST node representing a complete BSL agent specification.

    Parameters
    ----------
    name:
        The agent identifier.
    version:
        Optional version string (semver).
    model:
        Optional model identifier, e.g. ``"gpt-4o"``.
    owner:
        Optional owner / team name.
    behaviors:
        Ordered list of behavior declarations.
    invariants:
        Ordered list of invariant declarations.
    degradations:
        Degradation (fallback) rules.
    compositions:
        Composition (receives/delegates) clauses.
    span:
        Source location of the entire agent block.
    """

    name: str
    version: str | None
    model: str | None
    owner: str | None
    behaviors: tuple[Behavior, ...]
    invariants: tuple[Invariant, ...]
    degradations: tuple[Degradation, ...]
    compositions: tuple[Composition, ...]
    span: Span

    def get_behavior(self, name: str) -> Behavior | None:
        """Return the behavior with the given name, or ``None`` if absent."""
        for behavior in self.behaviors:
            if behavior.name == name:
                return behavior
        return None

    def get_invariant(self, name: str) -> Invariant | None:
        """Return the invariant with the given name, or ``None`` if absent."""
        for invariant in self.invariants:
            if invariant.name == name:
                return invariant
        return None

    @property
    def behavior_names(self) -> list[str]:
        """Sorted list of all behavior names in this spec."""
        return sorted(b.name for b in self.behaviors)

    @property
    def invariant_names(self) -> list[str]:
        """Sorted list of all invariant names in this spec."""
        return sorted(i.name for i in self.invariants)
