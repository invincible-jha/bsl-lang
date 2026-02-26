"""BSL Diff module.

Exports the ``BslDiff`` class and the ``diff`` convenience function,
plus all ``BslChange`` union member types.
"""
from __future__ import annotations

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
    diff,
)

__all__ = [
    "BslDiff",
    "diff",
    "BslChange",
    "ChangeKind",
    "BehaviorAdded",
    "BehaviorRemoved",
    "ConstraintAdded",
    "ConstraintRemoved",
    "ConstraintModified",
    "InvariantAdded",
    "InvariantRemoved",
    "ThresholdChanged",
    "SeverityChanged",
    "DegradationChanged",
    "CompositionAdded",
    "CompositionRemoved",
    "MetadataChanged",
    "WhenClauseChanged",
    "AuditLevelChanged",
    "EscalationChanged",
]
