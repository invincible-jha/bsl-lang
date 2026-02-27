"""Structural diff between two BSL ``AgentSpec`` AST trees.

The ``BslDiff`` class compares two ``AgentSpec`` objects and produces
an ordered list of ``BslChange`` objects describing what changed from
the old spec to the new spec.

Changes are purely structural — they compare the logical content of the
specs rather than byte-level text.  This makes the diff stable across
whitespace-only reformatting.

Usage
-----
::

    from bsl.diff import diff

    changes = diff(old_spec, new_spec)
    for change in changes:
        print(change)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Union

from bsl.ast.nodes import (
    AgentSpec,
    AuditLevel,
    Behavior,
    Composition,
    Constraint,
    Degradation,
    Delegates,
    Expression,
    Invariant,
    Receives,
    Severity,
    ShouldConstraint,
    ThresholdClause,
)


class ChangeKind(Enum):
    """Enumeration of all change kinds in a BSL diff."""

    BEHAVIOR_ADDED = auto()
    BEHAVIOR_REMOVED = auto()
    CONSTRAINT_ADDED = auto()
    CONSTRAINT_REMOVED = auto()
    CONSTRAINT_MODIFIED = auto()
    INVARIANT_ADDED = auto()
    INVARIANT_REMOVED = auto()
    THRESHOLD_CHANGED = auto()
    SEVERITY_CHANGED = auto()
    DEGRADATION_CHANGED = auto()
    COMPOSITION_ADDED = auto()
    COMPOSITION_REMOVED = auto()
    METADATA_CHANGED = auto()
    WHEN_CLAUSE_CHANGED = auto()
    AUDIT_LEVEL_CHANGED = auto()
    ESCALATION_CHANGED = auto()


# ---------------------------------------------------------------------------
# Change dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BehaviorAdded:
    """A new behavior was added in the new spec."""

    kind: ChangeKind = ChangeKind.BEHAVIOR_ADDED
    behavior_name: str = ""

    def __str__(self) -> str:
        return f"[+] Behavior '{self.behavior_name}' added"


@dataclass(frozen=True)
class BehaviorRemoved:
    """A behavior was removed in the new spec."""

    kind: ChangeKind = ChangeKind.BEHAVIOR_REMOVED
    behavior_name: str = ""

    def __str__(self) -> str:
        return f"[-] Behavior '{self.behavior_name}' removed"


@dataclass(frozen=True)
class ConstraintAdded:
    """A constraint was added to an existing behavior."""

    kind: ChangeKind = ChangeKind.CONSTRAINT_ADDED
    behavior_name: str = ""
    constraint_type: str = ""  # must, must_not, should, may
    expression: str = ""

    def __str__(self) -> str:
        return f"[+] {self.behavior_name}.{self.constraint_type}: {self.expression}"


@dataclass(frozen=True)
class ConstraintRemoved:
    """A constraint was removed from an existing behavior."""

    kind: ChangeKind = ChangeKind.CONSTRAINT_REMOVED
    behavior_name: str = ""
    constraint_type: str = ""
    expression: str = ""

    def __str__(self) -> str:
        return f"[-] {self.behavior_name}.{self.constraint_type}: {self.expression}"


@dataclass(frozen=True)
class ConstraintModified:
    """A constraint expression was changed in an existing behavior."""

    kind: ChangeKind = ChangeKind.CONSTRAINT_MODIFIED
    behavior_name: str = ""
    constraint_type: str = ""
    old_expression: str = ""
    new_expression: str = ""

    def __str__(self) -> str:
        return (
            f"[~] {self.behavior_name}.{self.constraint_type}: "
            f"{self.old_expression!r} → {self.new_expression!r}"
        )


@dataclass(frozen=True)
class InvariantAdded:
    """A new invariant was added."""

    kind: ChangeKind = ChangeKind.INVARIANT_ADDED
    invariant_name: str = ""

    def __str__(self) -> str:
        return f"[+] Invariant '{self.invariant_name}' added"


@dataclass(frozen=True)
class InvariantRemoved:
    """An invariant was removed."""

    kind: ChangeKind = ChangeKind.INVARIANT_REMOVED
    invariant_name: str = ""

    def __str__(self) -> str:
        return f"[-] Invariant '{self.invariant_name}' removed"


@dataclass(frozen=True)
class ThresholdChanged:
    """A threshold clause (confidence, latency, cost) changed."""

    kind: ChangeKind = ChangeKind.THRESHOLD_CHANGED
    behavior_name: str = ""
    field_name: str = ""  # confidence, latency, cost
    old_value: str = ""
    new_value: str = ""

    def __str__(self) -> str:
        return (
            f"[~] {self.behavior_name}.{self.field_name}: "
            f"{self.old_value} → {self.new_value}"
        )


@dataclass(frozen=True)
class SeverityChanged:
    """An invariant's severity level changed."""

    kind: ChangeKind = ChangeKind.SEVERITY_CHANGED
    invariant_name: str = ""
    old_severity: str = ""
    new_severity: str = ""

    def __str__(self) -> str:
        return (
            f"[~] Invariant '{self.invariant_name}' severity: "
            f"{self.old_severity} → {self.new_severity}"
        )


@dataclass(frozen=True)
class DegradationChanged:
    """A degradation rule changed (added, removed, or modified)."""

    kind: ChangeKind = ChangeKind.DEGRADATION_CHANGED
    description: str = ""

    def __str__(self) -> str:
        return f"[~] Degradation: {self.description}"


@dataclass(frozen=True)
class CompositionAdded:
    """A composition clause was added."""

    kind: ChangeKind = ChangeKind.COMPOSITION_ADDED
    description: str = ""

    def __str__(self) -> str:
        return f"[+] Composition: {self.description}"


@dataclass(frozen=True)
class CompositionRemoved:
    """A composition clause was removed."""

    kind: ChangeKind = ChangeKind.COMPOSITION_REMOVED
    description: str = ""

    def __str__(self) -> str:
        return f"[-] Composition: {self.description}"


@dataclass(frozen=True)
class MetadataChanged:
    """An agent-level metadata field changed (version, model, owner)."""

    kind: ChangeKind = ChangeKind.METADATA_CHANGED
    field_name: str = ""
    old_value: str | None = None
    new_value: str | None = None

    def __str__(self) -> str:
        return f"[~] {self.field_name}: {self.old_value!r} → {self.new_value!r}"


@dataclass(frozen=True)
class WhenClauseChanged:
    """A behavior's when clause changed."""

    kind: ChangeKind = ChangeKind.WHEN_CLAUSE_CHANGED
    behavior_name: str = ""
    old_when: str | None = None
    new_when: str | None = None

    def __str__(self) -> str:
        return f"[~] {self.behavior_name}.when: {self.old_when!r} → {self.new_when!r}"


@dataclass(frozen=True)
class AuditLevelChanged:
    """A behavior's audit level changed."""

    kind: ChangeKind = ChangeKind.AUDIT_LEVEL_CHANGED
    behavior_name: str = ""
    old_level: str = ""
    new_level: str = ""

    def __str__(self) -> str:
        return (
            f"[~] {self.behavior_name}.audit: {self.old_level} → {self.new_level}"
        )


@dataclass(frozen=True)
class EscalationChanged:
    """A behavior's escalation clause changed."""

    kind: ChangeKind = ChangeKind.ESCALATION_CHANGED
    behavior_name: str = ""
    description: str = ""

    def __str__(self) -> str:
        return f"[~] {self.behavior_name}.escalation: {self.description}"


BslChange = Union[
    BehaviorAdded,
    BehaviorRemoved,
    ConstraintAdded,
    ConstraintRemoved,
    ConstraintModified,
    InvariantAdded,
    InvariantRemoved,
    ThresholdChanged,
    SeverityChanged,
    DegradationChanged,
    CompositionAdded,
    CompositionRemoved,
    MetadataChanged,
    WhenClauseChanged,
    AuditLevelChanged,
    EscalationChanged,
]


# ---------------------------------------------------------------------------
# Helper: expression → string (for display in diffs)
# ---------------------------------------------------------------------------


def _expr_str(expr: Expression | None) -> str:
    """Return a compact string representation of any expression node."""
    from bsl.ast.nodes import (
        AfterExpr,
        BeforeExpr,
        BinaryOpExpr,
        BoolLit,
        ContainsExpr,
        DotAccess,
        FunctionCall,
        Identifier,
        InListExpr,
        NumberLit,
        StringLit,
        UnaryOpExpr,
    )

    if expr is None:
        return "<none>"
    if isinstance(expr, Identifier):
        return expr.name
    if isinstance(expr, DotAccess):
        return ".".join(expr.parts)
    if isinstance(expr, StringLit):
        return f'"{expr.value}"'
    if isinstance(expr, NumberLit):
        return str(expr.value)
    if isinstance(expr, BoolLit):
        return str(expr.value).lower()
    if isinstance(expr, BinaryOpExpr):
        return f"{_expr_str(expr.left)} {expr.op.name.lower()} {_expr_str(expr.right)}"
    if isinstance(expr, UnaryOpExpr):
        return f"not {_expr_str(expr.operand)}"
    if isinstance(expr, ContainsExpr):
        return f"{_expr_str(expr.subject)} contains {_expr_str(expr.value)}"
    if isinstance(expr, InListExpr):
        items = ", ".join(_expr_str(i) for i in expr.items)
        return f"{_expr_str(expr.subject)} in [{items}]"
    if isinstance(expr, BeforeExpr):
        return f"{_expr_str(expr.left)} before {_expr_str(expr.right)}"
    if isinstance(expr, AfterExpr):
        return f"{_expr_str(expr.left)} after {_expr_str(expr.right)}"
    if isinstance(expr, FunctionCall):
        args = ", ".join(_expr_str(a) for a in expr.arguments)
        return f"{expr.name}({args})"
    return repr(expr)


def _threshold_str(t: ThresholdClause | None) -> str:
    if t is None:
        return "<none>"
    pct = "%" if t.is_percentage else ""
    return f"{t.operator}{t.value}{pct}"


def _composition_str(c: Composition) -> str:
    if isinstance(c, Receives):
        return f"receives from {c.source_agent}"
    if isinstance(c, Delegates):
        return f"delegates_to {c.target_agent}"
    return repr(c)


# ---------------------------------------------------------------------------
# BslDiff class
# ---------------------------------------------------------------------------


class BslDiff:
    """Computes structural changes between two ``AgentSpec`` AST trees."""

    def diff(self, old: AgentSpec, new: AgentSpec) -> list[BslChange]:
        """Return all changes from ``old`` to ``new``.

        Parameters
        ----------
        old:
            The baseline agent specification.
        new:
            The updated agent specification.

        Returns
        -------
        list[BslChange]
            Ordered list of changes.  Empty if the specs are semantically
            identical (ignoring spans and source positions).
        """
        changes: list[BslChange] = []
        changes.extend(self._diff_metadata(old, new))
        changes.extend(self._diff_behaviors(old, new))
        changes.extend(self._diff_invariants(old, new))
        changes.extend(self._diff_degradations(old, new))
        changes.extend(self._diff_compositions(old, new))
        return changes

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _diff_metadata(self, old: AgentSpec, new: AgentSpec) -> list[BslChange]:
        changes: list[BslChange] = []
        for field_name in ("version", "model", "owner"):
            old_val = getattr(old, field_name)
            new_val = getattr(new, field_name)
            if old_val != new_val:
                changes.append(
                    MetadataChanged(field_name=field_name, old_value=old_val, new_value=new_val)
                )
        return changes

    # ------------------------------------------------------------------
    # Behaviors
    # ------------------------------------------------------------------

    def _diff_behaviors(self, old: AgentSpec, new: AgentSpec) -> list[BslChange]:
        changes: list[BslChange] = []
        old_map = {b.name: b for b in old.behaviors}
        new_map = {b.name: b for b in new.behaviors}

        for name in sorted(old_map.keys() - new_map.keys()):
            changes.append(BehaviorRemoved(behavior_name=name))

        for name in sorted(new_map.keys() - old_map.keys()):
            changes.append(BehaviorAdded(behavior_name=name))

        for name in sorted(old_map.keys() & new_map.keys()):
            changes.extend(self._diff_behavior(name, old_map[name], new_map[name]))

        return changes

    def _diff_behavior(
        self, name: str, old: Behavior, new: Behavior
    ) -> list[BslChange]:
        changes: list[BslChange] = []

        # when clause
        old_when = _expr_str(old.when_clause) if old.when_clause else None
        new_when = _expr_str(new.when_clause) if new.when_clause else None
        if old_when != new_when:
            changes.append(WhenClauseChanged(behavior_name=name, old_when=old_when, new_when=new_when))

        # thresholds
        for field_name in ("confidence", "latency", "cost"):
            old_t = getattr(old, field_name)
            new_t = getattr(new, field_name)
            old_s = _threshold_str(old_t)
            new_s = _threshold_str(new_t)
            if old_s != new_s:
                changes.append(ThresholdChanged(
                    behavior_name=name,
                    field_name=field_name,
                    old_value=old_s,
                    new_value=new_s,
                ))

        # audit level
        if old.audit != new.audit:
            changes.append(AuditLevelChanged(
                behavior_name=name,
                old_level=old.audit.name,
                new_level=new.audit.name,
            ))

        # escalation
        old_esc = _expr_str(old.escalation.condition) if old.escalation else None
        new_esc = _expr_str(new.escalation.condition) if new.escalation else None
        if old_esc != new_esc:
            changes.append(EscalationChanged(
                behavior_name=name,
                description=f"{old_esc!r} → {new_esc!r}",
            ))

        # constraints
        for ctype in ("must", "must_not", "should", "may"):
            changes.extend(
                self._diff_constraints(
                    name,
                    ctype,
                    getattr(old, f"{ctype}_constraints"),
                    getattr(new, f"{ctype}_constraints"),
                )
            )

        return changes

    def _diff_constraints(
        self,
        behavior_name: str,
        constraint_type: str,
        old_list: tuple[Constraint | ShouldConstraint, ...],
        new_list: tuple[Constraint | ShouldConstraint, ...],
    ) -> list[BslChange]:
        changes: list[BslChange] = []
        old_exprs = [_expr_str(c.expression) for c in old_list]
        new_exprs = [_expr_str(c.expression) for c in new_list]
        old_set = set(old_exprs)
        new_set = set(new_exprs)

        for expr in sorted(old_set - new_set):
            changes.append(ConstraintRemoved(
                behavior_name=behavior_name,
                constraint_type=constraint_type,
                expression=expr,
            ))
        for expr in sorted(new_set - old_set):
            changes.append(ConstraintAdded(
                behavior_name=behavior_name,
                constraint_type=constraint_type,
                expression=expr,
            ))
        return changes

    # ------------------------------------------------------------------
    # Invariants
    # ------------------------------------------------------------------

    def _diff_invariants(self, old: AgentSpec, new: AgentSpec) -> list[BslChange]:
        changes: list[BslChange] = []
        old_map = {i.name: i for i in old.invariants}
        new_map = {i.name: i for i in new.invariants}

        for name in sorted(old_map.keys() - new_map.keys()):
            changes.append(InvariantRemoved(invariant_name=name))
        for name in sorted(new_map.keys() - old_map.keys()):
            changes.append(InvariantAdded(invariant_name=name))

        for name in sorted(old_map.keys() & new_map.keys()):
            old_inv = old_map[name]
            new_inv = new_map[name]
            if old_inv.severity != new_inv.severity:
                changes.append(SeverityChanged(
                    invariant_name=name,
                    old_severity=old_inv.severity.name,
                    new_severity=new_inv.severity.name,
                ))

        return changes

    # ------------------------------------------------------------------
    # Degradations
    # ------------------------------------------------------------------

    def _diff_degradations(self, old: AgentSpec, new: AgentSpec) -> list[BslChange]:
        changes: list[BslChange] = []
        old_map = {d.fallback: _expr_str(d.condition) for d in old.degradations}
        new_map = {d.fallback: _expr_str(d.condition) for d in new.degradations}

        for fallback in sorted(old_map.keys() - new_map.keys()):
            changes.append(DegradationChanged(
                description=f"Removed: degrades_to {fallback}"
            ))
        for fallback in sorted(new_map.keys() - old_map.keys()):
            changes.append(DegradationChanged(
                description=f"Added: degrades_to {fallback}"
            ))
        for fallback in sorted(old_map.keys() & new_map.keys()):
            if old_map[fallback] != new_map[fallback]:
                changes.append(DegradationChanged(
                    description=(
                        f"degrades_to {fallback}: condition changed from "
                        f"{old_map[fallback]!r} to {new_map[fallback]!r}"
                    )
                ))
        return changes

    # ------------------------------------------------------------------
    # Compositions
    # ------------------------------------------------------------------

    def _diff_compositions(self, old: AgentSpec, new: AgentSpec) -> list[BslChange]:
        changes: list[BslChange] = []
        old_strs = {_composition_str(c) for c in old.compositions}
        new_strs = {_composition_str(c) for c in new.compositions}

        for s in sorted(old_strs - new_strs):
            changes.append(CompositionRemoved(description=s))
        for s in sorted(new_strs - old_strs):
            changes.append(CompositionAdded(description=s))
        return changes


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


def diff(old: AgentSpec, new: AgentSpec) -> list[BslChange]:
    """Compare two ``AgentSpec`` objects and return the list of changes.

    Parameters
    ----------
    old:
        The baseline specification.
    new:
        The updated specification.

    Returns
    -------
    list[BslChange]
        All structural changes from ``old`` to ``new``.

    Example
    -------
    ::

        from bsl.diff import diff
        changes = diff(old_spec, new_spec)
        for change in changes:
            print(change)
    """
    return BslDiff().diff(old, new)
