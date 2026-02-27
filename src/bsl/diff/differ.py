"""Semantic differ for BSL AgentSpec AST trees.

BslDiffer wraps the lower-level ``BslDiff`` implementation with a richer
interface that provides path-aware change reporting and structured
:class:`DiffResult` summaries.

Usage
-----
::

    from bsl.diff.differ import BslDiffer, DiffResult

    differ = BslDiffer()
    result = differ.compare(old_spec, new_spec)
    print(result.summary())
    for item in result.items:
        print(item)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from bsl.ast.nodes import AgentSpec
from bsl.diff.diff import (
    AuditLevelChanged,
    BehaviorAdded,
    BehaviorRemoved,
    BslChange,
    BslDiff,
    ChangeKind,
    CompositionAdded,
    CompositionRemoved,
    ConstraintAdded,
    ConstraintModified,
    ConstraintRemoved,
    DegradationChanged,
    EscalationChanged,
    InvariantAdded,
    InvariantRemoved,
    MetadataChanged,
    SeverityChanged,
    ThresholdChanged,
    WhenClauseChanged,
)


# ---------------------------------------------------------------------------
# DiffItem — path-annotated change record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DiffItem:
    """A single annotated change with a hierarchical path.

    Parameters
    ----------
    path:
        Dot-separated path to the changed element, e.g.
        ``"behaviors.handle_query.must_constraints"``.
    kind:
        The :class:`ChangeKind` enum value describing what changed.
    description:
        Human-readable description of the change.
    old_value:
        The value before the change (may be ``None`` for additions).
    new_value:
        The value after the change (may be ``None`` for removals).
    severity:
        Importance level: ``"breaking"``, ``"warning"``, ``"info"``.
    """

    path: str
    kind: ChangeKind
    description: str
    old_value: str | None = None
    new_value: str | None = None
    severity: str = "info"

    def __str__(self) -> str:
        tag = {"breaking": "!!", "warning": "~~", "info": "  "}.get(self.severity, "  ")
        return f"[{tag}] {self.path}: {self.description}"


# ---------------------------------------------------------------------------
# DiffResult — collection of DiffItems with summary helpers
# ---------------------------------------------------------------------------


@dataclass
class DiffResult:
    """Structured result of comparing two AgentSpec AST trees.

    Parameters
    ----------
    old_agent:
        Name of the old agent spec.
    new_agent:
        Name of the new agent spec.
    items:
        All annotated change items found during comparison.
    raw_changes:
        The raw :class:`BslChange` objects from the lower-level diff.
    """

    old_agent: str
    new_agent: str
    items: list[DiffItem] = field(default_factory=list)
    raw_changes: list[BslChange] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Return ``True`` when any differences were found."""
        return bool(self.items)

    @property
    def breaking_count(self) -> int:
        """Number of breaking changes."""
        return sum(1 for item in self.items if item.severity == "breaking")

    @property
    def warning_count(self) -> int:
        """Number of warning-level changes."""
        return sum(1 for item in self.items if item.severity == "warning")

    @property
    def info_count(self) -> int:
        """Number of informational changes."""
        return sum(1 for item in self.items if item.severity == "info")

    def by_kind(self, kind: ChangeKind) -> list[DiffItem]:
        """Return all items with a specific :class:`ChangeKind`."""
        return [item for item in self.items if item.kind == kind]

    def by_path_prefix(self, prefix: str) -> list[DiffItem]:
        """Return all items whose path starts with *prefix*."""
        return [item for item in self.items if item.path.startswith(prefix)]

    def summary(self) -> str:
        """Return a multi-line human-readable summary of the diff."""
        if not self.has_changes:
            return (
                f"No changes between '{self.old_agent}' and '{self.new_agent}'."
            )
        lines = [
            f"Diff: '{self.old_agent}' → '{self.new_agent}'",
            f"  {len(self.items)} change(s): "
            f"{self.breaking_count} breaking, "
            f"{self.warning_count} warnings, "
            f"{self.info_count} info",
            "",
        ]
        for item in self.items:
            lines.append(f"  {item}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        """Serialise the result to a plain dictionary for JSON output."""
        return {
            "old_agent": self.old_agent,
            "new_agent": self.new_agent,
            "total_changes": len(self.items),
            "breaking": self.breaking_count,
            "warnings": self.warning_count,
            "info": self.info_count,
            "items": [
                {
                    "path": item.path,
                    "kind": item.kind.name,
                    "description": item.description,
                    "old_value": item.old_value,
                    "new_value": item.new_value,
                    "severity": item.severity,
                }
                for item in self.items
            ],
        }


# ---------------------------------------------------------------------------
# Severity classification helpers
# ---------------------------------------------------------------------------

# Changes that break backward compatibility (removed constraints, invariants, compositions)
_BREAKING_KINDS: frozenset[ChangeKind] = frozenset(
    {
        ChangeKind.BEHAVIOR_REMOVED,
        ChangeKind.INVARIANT_REMOVED,
        ChangeKind.CONSTRAINT_REMOVED,
        ChangeKind.COMPOSITION_REMOVED,
    }
)

# Changes that should be reviewed carefully
_WARNING_KINDS: frozenset[ChangeKind] = frozenset(
    {
        ChangeKind.SEVERITY_CHANGED,
        ChangeKind.THRESHOLD_CHANGED,
        ChangeKind.ESCALATION_CHANGED,
        ChangeKind.WHEN_CLAUSE_CHANGED,
        ChangeKind.CONSTRAINT_MODIFIED,
        ChangeKind.DEGRADATION_CHANGED,
    }
)


def _classify_severity(kind: ChangeKind) -> str:
    if kind in _BREAKING_KINDS:
        return "breaking"
    if kind in _WARNING_KINDS:
        return "warning"
    return "info"


# ---------------------------------------------------------------------------
# BslDiffer
# ---------------------------------------------------------------------------


class BslDiffer:
    """Semantic differ for BSL ``AgentSpec`` AST trees.

    Produces a :class:`DiffResult` that annotates every change with a
    hierarchical path, severity level, and structured old/new values.

    The differ delegates raw change detection to the lower-level
    :class:`~bsl.diff.diff.BslDiff` and enriches each change with
    path information.

    Example
    -------
    ::

        from bsl.diff.differ import BslDiffer

        differ = BslDiffer()
        result = differ.compare(old_spec, new_spec)
        if result.has_changes:
            print(result.summary())
    """

    def __init__(self) -> None:
        self._low_level = BslDiff()

    def compare(self, old: AgentSpec, new: AgentSpec) -> DiffResult:
        """Compare two :class:`~bsl.ast.nodes.AgentSpec` trees.

        Parameters
        ----------
        old:
            The baseline specification.
        new:
            The updated specification.

        Returns
        -------
        DiffResult
            Structured result containing all annotated change items.
        """
        raw_changes = self._low_level.diff(old, new)
        items = [self._annotate(change) for change in raw_changes]
        return DiffResult(
            old_agent=old.name,
            new_agent=new.name,
            items=items,
            raw_changes=raw_changes,
        )

    def _annotate(self, change: BslChange) -> DiffItem:
        """Convert a raw :class:`BslChange` into a path-annotated :class:`DiffItem`."""
        kind = change.kind

        if isinstance(change, BehaviorAdded):
            return DiffItem(
                path=f"behaviors.{change.behavior_name}",
                kind=kind,
                description=f"Behavior '{change.behavior_name}' added",
                new_value=change.behavior_name,
                severity=_classify_severity(kind),
            )

        if isinstance(change, BehaviorRemoved):
            return DiffItem(
                path=f"behaviors.{change.behavior_name}",
                kind=kind,
                description=f"Behavior '{change.behavior_name}' removed",
                old_value=change.behavior_name,
                severity=_classify_severity(kind),
            )

        if isinstance(change, ConstraintAdded):
            return DiffItem(
                path=f"behaviors.{change.behavior_name}.{change.constraint_type}_constraints",
                kind=kind,
                description=(
                    f"Constraint added to '{change.behavior_name}' "
                    f"({change.constraint_type}): {change.expression}"
                ),
                new_value=change.expression,
                severity=_classify_severity(kind),
            )

        if isinstance(change, ConstraintRemoved):
            return DiffItem(
                path=f"behaviors.{change.behavior_name}.{change.constraint_type}_constraints",
                kind=kind,
                description=(
                    f"Constraint removed from '{change.behavior_name}' "
                    f"({change.constraint_type}): {change.expression}"
                ),
                old_value=change.expression,
                severity=_classify_severity(kind),
            )

        if isinstance(change, ConstraintModified):
            return DiffItem(
                path=f"behaviors.{change.behavior_name}.{change.constraint_type}_constraints",
                kind=kind,
                description=(
                    f"Constraint modified in '{change.behavior_name}' ({change.constraint_type})"
                ),
                old_value=change.old_expression,
                new_value=change.new_expression,
                severity=_classify_severity(kind),
            )

        if isinstance(change, InvariantAdded):
            return DiffItem(
                path=f"invariants.{change.invariant_name}",
                kind=kind,
                description=f"Invariant '{change.invariant_name}' added",
                new_value=change.invariant_name,
                severity=_classify_severity(kind),
            )

        if isinstance(change, InvariantRemoved):
            return DiffItem(
                path=f"invariants.{change.invariant_name}",
                kind=kind,
                description=f"Invariant '{change.invariant_name}' removed",
                old_value=change.invariant_name,
                severity=_classify_severity(kind),
            )

        if isinstance(change, ThresholdChanged):
            return DiffItem(
                path=f"behaviors.{change.behavior_name}.{change.field_name}",
                kind=kind,
                description=(
                    f"Threshold '{change.field_name}' changed in '{change.behavior_name}'"
                ),
                old_value=change.old_value,
                new_value=change.new_value,
                severity=_classify_severity(kind),
            )

        if isinstance(change, SeverityChanged):
            return DiffItem(
                path=f"invariants.{change.invariant_name}.severity",
                kind=kind,
                description=(
                    f"Severity of invariant '{change.invariant_name}' changed"
                ),
                old_value=change.old_severity,
                new_value=change.new_severity,
                severity=_classify_severity(kind),
            )

        if isinstance(change, DegradationChanged):
            return DiffItem(
                path="degradations",
                kind=kind,
                description=change.description,
                severity=_classify_severity(kind),
            )

        if isinstance(change, CompositionAdded):
            return DiffItem(
                path="compositions",
                kind=kind,
                description=f"Composition added: {change.description}",
                new_value=change.description,
                severity=_classify_severity(kind),
            )

        if isinstance(change, CompositionRemoved):
            return DiffItem(
                path="compositions",
                kind=kind,
                description=f"Composition removed: {change.description}",
                old_value=change.description,
                severity=_classify_severity(kind),
            )

        if isinstance(change, MetadataChanged):
            return DiffItem(
                path=f"metadata.{change.field_name}",
                kind=kind,
                description=f"Metadata field '{change.field_name}' changed",
                old_value=change.old_value,
                new_value=change.new_value,
                severity=_classify_severity(kind),
            )

        if isinstance(change, WhenClauseChanged):
            return DiffItem(
                path=f"behaviors.{change.behavior_name}.when",
                kind=kind,
                description=f"When clause changed in '{change.behavior_name}'",
                old_value=change.old_when,
                new_value=change.new_when,
                severity=_classify_severity(kind),
            )

        if isinstance(change, AuditLevelChanged):
            return DiffItem(
                path=f"behaviors.{change.behavior_name}.audit",
                kind=kind,
                description=(
                    f"Audit level changed in '{change.behavior_name}': "
                    f"{change.old_level} → {change.new_level}"
                ),
                old_value=change.old_level,
                new_value=change.new_level,
                severity=_classify_severity(kind),
            )

        if isinstance(change, EscalationChanged):
            return DiffItem(
                path=f"behaviors.{change.behavior_name}.escalation",
                kind=kind,
                description=f"Escalation changed in '{change.behavior_name}'",
                severity=_classify_severity(kind),
            )

        # Fallback for any future change kinds
        return DiffItem(
            path="unknown",
            kind=kind,
            description=str(change),
            severity="info",
        )
