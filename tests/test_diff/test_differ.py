"""Tests for bsl.diff.differ — BslDiffer, DiffItem, and DiffResult."""
from __future__ import annotations

import pytest

from bsl.ast.nodes import (
    AgentSpec,
    AppliesTo,
    AuditLevel,
    Behavior,
    Composition,
    Constraint,
    Degradation,
    Delegates,
    EscalationClause,
    Identifier,
    Invariant,
    Receives,
    Severity,
    ShouldConstraint,
    Span,
    ThresholdClause,
)
from bsl.diff.diff import ChangeKind
from bsl.diff.differ import BslDiffer, DiffItem, DiffResult

_S = Span.unknown()


# ---------------------------------------------------------------------------
# Test helpers (mirrors test_diff.py conventions)
# ---------------------------------------------------------------------------


def _ident(name: str) -> Identifier:
    return Identifier(name=name, span=_S)


def _constraint(name: str) -> Constraint:
    return Constraint(expression=_ident(name), span=_S)


def _should(name: str) -> ShouldConstraint:
    return ShouldConstraint(expression=_ident(name), percentage=None, span=_S)


def _threshold(op: str, value: float) -> ThresholdClause:
    return ThresholdClause(operator=op, value=value, is_percentage=False, span=_S)


def _escalation(cond: str) -> EscalationClause:
    return EscalationClause(condition=_ident(cond), span=_S)


def _behavior(
    name: str,
    *,
    when_clause: object | None = None,
    must: tuple[Constraint, ...] = (),
    must_not: tuple[Constraint, ...] = (),
    should: tuple[ShouldConstraint, ...] = (),
    may: tuple[Constraint, ...] = (),
    confidence: ThresholdClause | None = None,
    latency: ThresholdClause | None = None,
    cost: ThresholdClause | None = None,
    escalation: EscalationClause | None = None,
    audit: AuditLevel = AuditLevel.NONE,
) -> Behavior:
    return Behavior(
        name=name,
        when_clause=when_clause,  # type: ignore[arg-type]
        must_constraints=must,
        must_not_constraints=must_not,
        should_constraints=should,
        may_constraints=may,
        confidence=confidence,
        latency=latency,
        cost=cost,
        escalation=escalation,
        audit=audit,
        span=_S,
    )


def _invariant(
    name: str,
    *,
    severity: Severity = Severity.HIGH,
    constraints: tuple[Constraint, ...] = (),
    prohibitions: tuple[Constraint, ...] = (),
) -> Invariant:
    return Invariant(
        name=name,
        constraints=constraints,
        prohibitions=prohibitions,
        applies_to=AppliesTo.ALL_BEHAVIORS,
        named_behaviors=(),
        severity=severity,
        span=_S,
    )


def _spec(
    name: str = "TestAgent",
    *,
    version: str | None = "1.0.0",
    model: str | None = "gpt-4o",
    owner: str | None = "team@example.com",
    behaviors: tuple[Behavior, ...] = (),
    invariants: tuple[Invariant, ...] = (),
    degradations: tuple[Degradation, ...] = (),
    compositions: tuple[Composition, ...] = (),
) -> AgentSpec:
    return AgentSpec(
        name=name,
        version=version,
        model=model,
        owner=owner,
        behaviors=behaviors,
        invariants=invariants,
        degradations=degradations,
        compositions=compositions,
        span=_S,
    )


# ===========================================================================
# DiffItem
# ===========================================================================


class TestDiffItem:
    def test_str_breaking(self) -> None:
        item = DiffItem(
            path="behaviors.respond",
            kind=ChangeKind.BEHAVIOR_REMOVED,
            description="Behavior removed",
            severity="breaking",
        )
        text = str(item)
        assert "!!" in text
        assert "behaviors.respond" in text

    def test_str_warning(self) -> None:
        item = DiffItem(
            path="behaviors.b.confidence",
            kind=ChangeKind.THRESHOLD_CHANGED,
            description="Threshold changed",
            severity="warning",
        )
        text = str(item)
        assert "~~" in text

    def test_str_info(self) -> None:
        item = DiffItem(
            path="behaviors.greet",
            kind=ChangeKind.BEHAVIOR_ADDED,
            description="Behavior added",
            severity="info",
        )
        text = str(item)
        assert "behaviors.greet" in text

    def test_frozen(self) -> None:
        item = DiffItem(
            path="p",
            kind=ChangeKind.BEHAVIOR_ADDED,
            description="desc",
        )
        with pytest.raises((AttributeError, TypeError)):
            item.path = "other"  # type: ignore[misc]

    def test_defaults(self) -> None:
        item = DiffItem(
            path="p",
            kind=ChangeKind.BEHAVIOR_ADDED,
            description="desc",
        )
        assert item.old_value is None
        assert item.new_value is None
        assert item.severity == "info"


# ===========================================================================
# DiffResult
# ===========================================================================


class TestDiffResult:
    def _make_result(self, items: list[DiffItem]) -> DiffResult:
        return DiffResult(old_agent="OldAgent", new_agent="NewAgent", items=items)

    def test_has_changes_empty(self) -> None:
        result = self._make_result([])
        assert not result.has_changes

    def test_has_changes_with_items(self) -> None:
        item = DiffItem(
            path="p", kind=ChangeKind.BEHAVIOR_ADDED, description="d", severity="info"
        )
        result = self._make_result([item])
        assert result.has_changes

    def test_breaking_count(self) -> None:
        items = [
            DiffItem("p1", ChangeKind.BEHAVIOR_REMOVED, "d", severity="breaking"),
            DiffItem("p2", ChangeKind.CONSTRAINT_REMOVED, "d", severity="breaking"),
            DiffItem("p3", ChangeKind.BEHAVIOR_ADDED, "d", severity="info"),
        ]
        result = self._make_result(items)
        assert result.breaking_count == 2

    def test_warning_count(self) -> None:
        items = [
            DiffItem("p1", ChangeKind.THRESHOLD_CHANGED, "d", severity="warning"),
            DiffItem("p2", ChangeKind.BEHAVIOR_ADDED, "d", severity="info"),
        ]
        result = self._make_result(items)
        assert result.warning_count == 1

    def test_info_count(self) -> None:
        items = [
            DiffItem("p1", ChangeKind.BEHAVIOR_ADDED, "d", severity="info"),
            DiffItem("p2", ChangeKind.INVARIANT_ADDED, "d", severity="info"),
            DiffItem("p3", ChangeKind.BEHAVIOR_REMOVED, "d", severity="breaking"),
        ]
        result = self._make_result(items)
        assert result.info_count == 2

    def test_by_kind(self) -> None:
        items = [
            DiffItem("p1", ChangeKind.BEHAVIOR_ADDED, "d"),
            DiffItem("p2", ChangeKind.BEHAVIOR_ADDED, "d"),
            DiffItem("p3", ChangeKind.INVARIANT_ADDED, "d"),
        ]
        result = self._make_result(items)
        assert len(result.by_kind(ChangeKind.BEHAVIOR_ADDED)) == 2
        assert len(result.by_kind(ChangeKind.INVARIANT_ADDED)) == 1
        assert len(result.by_kind(ChangeKind.BEHAVIOR_REMOVED)) == 0

    def test_by_path_prefix(self) -> None:
        items = [
            DiffItem("behaviors.respond.must_constraints", ChangeKind.CONSTRAINT_ADDED, "d"),
            DiffItem("behaviors.greet", ChangeKind.BEHAVIOR_ADDED, "d"),
            DiffItem("invariants.safety", ChangeKind.INVARIANT_ADDED, "d"),
        ]
        result = self._make_result(items)
        behavior_items = result.by_path_prefix("behaviors.")
        assert len(behavior_items) == 2
        invariant_items = result.by_path_prefix("invariants.")
        assert len(invariant_items) == 1

    def test_summary_no_changes(self) -> None:
        result = self._make_result([])
        summary = result.summary()
        assert "No changes" in summary
        assert "OldAgent" in summary
        assert "NewAgent" in summary

    def test_summary_with_changes(self) -> None:
        items = [
            DiffItem("behaviors.greet", ChangeKind.BEHAVIOR_ADDED, "Behavior added"),
        ]
        result = self._make_result(items)
        summary = result.summary()
        assert "OldAgent" in summary
        assert "NewAgent" in summary
        assert "1 change" in summary

    def test_to_dict_structure(self) -> None:
        items = [
            DiffItem(
                path="behaviors.b",
                kind=ChangeKind.BEHAVIOR_REMOVED,
                description="Removed",
                old_value="b",
                severity="breaking",
            )
        ]
        result = self._make_result(items)
        data = result.to_dict()
        assert data["old_agent"] == "OldAgent"
        assert data["new_agent"] == "NewAgent"
        assert data["total_changes"] == 1
        assert data["breaking"] == 1
        assert len(data["items"]) == 1
        item_dict = data["items"][0]
        assert item_dict["kind"] == "BEHAVIOR_REMOVED"
        assert item_dict["severity"] == "breaking"
        assert item_dict["path"] == "behaviors.b"


# ===========================================================================
# BslDiffer — integration tests
# ===========================================================================


class TestBslDifferBasic:
    def setup_method(self) -> None:
        self.differ = BslDiffer()

    def test_identical_specs_no_changes(self) -> None:
        spec = _spec()
        result = self.differ.compare(spec, spec)
        assert not result.has_changes
        assert result.items == []

    def test_returns_diff_result_type(self) -> None:
        spec = _spec()
        result = self.differ.compare(spec, spec)
        assert isinstance(result, DiffResult)

    def test_agent_names_captured(self) -> None:
        old = _spec("AgentOld")
        new = _spec("AgentNew")
        result = self.differ.compare(old, new)
        assert result.old_agent == "AgentOld"
        assert result.new_agent == "AgentNew"

    def test_raw_changes_populated(self) -> None:
        old = _spec()
        new = _spec(behaviors=(_behavior("greet"),))
        result = self.differ.compare(old, new)
        assert len(result.raw_changes) > 0

    def test_behavior_added_produces_info_item(self) -> None:
        old = _spec()
        new = _spec(behaviors=(_behavior("greet"),))
        result = self.differ.compare(old, new)
        added = result.by_kind(ChangeKind.BEHAVIOR_ADDED)
        assert len(added) == 1
        assert added[0].severity == "info"
        assert added[0].path == "behaviors.greet"
        assert added[0].new_value == "greet"

    def test_behavior_removed_produces_breaking_item(self) -> None:
        old = _spec(behaviors=(_behavior("greet"),))
        new = _spec()
        result = self.differ.compare(old, new)
        removed = result.by_kind(ChangeKind.BEHAVIOR_REMOVED)
        assert len(removed) == 1
        assert removed[0].severity == "breaking"
        assert removed[0].old_value == "greet"

    def test_constraint_added_produces_info_item(self) -> None:
        old = _spec(behaviors=(_behavior("respond"),))
        new = _spec(behaviors=(_behavior("respond", must=(_constraint("safe"),)),))
        result = self.differ.compare(old, new)
        added = result.by_kind(ChangeKind.CONSTRAINT_ADDED)
        assert len(added) == 1
        assert added[0].severity == "info"
        assert "respond" in added[0].path
        assert "must" in added[0].path

    def test_constraint_removed_produces_breaking_item(self) -> None:
        old = _spec(behaviors=(_behavior("respond", must=(_constraint("safe"),)),))
        new = _spec(behaviors=(_behavior("respond"),))
        result = self.differ.compare(old, new)
        removed = result.by_kind(ChangeKind.CONSTRAINT_REMOVED)
        assert len(removed) == 1
        assert removed[0].severity == "breaking"

    def test_invariant_added_produces_info_item(self) -> None:
        old = _spec()
        new = _spec(invariants=(_invariant("safety"),))
        result = self.differ.compare(old, new)
        items = result.by_kind(ChangeKind.INVARIANT_ADDED)
        assert len(items) == 1
        assert items[0].path == "invariants.safety"
        assert items[0].severity == "info"

    def test_invariant_removed_produces_breaking_item(self) -> None:
        old = _spec(invariants=(_invariant("safety"),))
        new = _spec()
        result = self.differ.compare(old, new)
        items = result.by_kind(ChangeKind.INVARIANT_REMOVED)
        assert len(items) == 1
        assert items[0].severity == "breaking"
        assert items[0].path == "invariants.safety"

    def test_severity_changed_produces_warning_item(self) -> None:
        old = _spec(invariants=(_invariant("safety", severity=Severity.HIGH),))
        new = _spec(invariants=(_invariant("safety", severity=Severity.CRITICAL),))
        result = self.differ.compare(old, new)
        items = result.by_kind(ChangeKind.SEVERITY_CHANGED)
        assert len(items) == 1
        assert items[0].severity == "warning"
        assert items[0].old_value == "HIGH"
        assert items[0].new_value == "CRITICAL"

    def test_threshold_changed_produces_warning_item(self) -> None:
        old = _spec(behaviors=(_behavior("b", confidence=_threshold(">=", 0.9)),))
        new = _spec(behaviors=(_behavior("b", confidence=_threshold(">=", 0.95)),))
        result = self.differ.compare(old, new)
        items = result.by_kind(ChangeKind.THRESHOLD_CHANGED)
        assert len(items) == 1
        assert items[0].severity == "warning"
        assert "confidence" in items[0].path

    def test_metadata_version_changed_produces_info_item(self) -> None:
        old = _spec(version="1.0.0")
        new = _spec(version="2.0.0")
        result = self.differ.compare(old, new)
        items = result.by_kind(ChangeKind.METADATA_CHANGED)
        assert any("version" in item.path for item in items)

    def test_when_clause_changed_produces_warning_item(self) -> None:
        old = _spec(behaviors=(_behavior("b", when_clause=_ident("cond_a")),))
        new = _spec(behaviors=(_behavior("b", when_clause=_ident("cond_b")),))
        result = self.differ.compare(old, new)
        items = result.by_kind(ChangeKind.WHEN_CLAUSE_CHANGED)
        assert len(items) == 1
        assert items[0].severity == "warning"
        assert ".when" in items[0].path

    def test_audit_level_changed_produces_info_item(self) -> None:
        old = _spec(behaviors=(_behavior("b", audit=AuditLevel.NONE),))
        new = _spec(behaviors=(_behavior("b", audit=AuditLevel.FULL_TRACE),))
        result = self.differ.compare(old, new)
        items = result.by_kind(ChangeKind.AUDIT_LEVEL_CHANGED)
        assert len(items) == 1
        assert ".audit" in items[0].path
        assert items[0].old_value == "NONE"
        assert items[0].new_value == "FULL_TRACE"

    def test_escalation_changed_produces_warning_item(self) -> None:
        old = _spec(behaviors=(_behavior("b", escalation=_escalation("angry")),))
        new = _spec(behaviors=(_behavior("b", escalation=_escalation("confused")),))
        result = self.differ.compare(old, new)
        items = result.by_kind(ChangeKind.ESCALATION_CHANGED)
        assert len(items) == 1
        assert items[0].severity == "warning"

    def test_degradation_changed_produces_warning_item(self) -> None:
        deg = Degradation(fallback="fallback", condition=_ident("overloaded"), span=_S)
        old = _spec()
        new = _spec(degradations=(deg,))
        result = self.differ.compare(old, new)
        items = result.by_kind(ChangeKind.DEGRADATION_CHANGED)
        assert len(items) == 1
        assert items[0].severity == "warning"
        assert items[0].path == "degradations"

    def test_composition_added_produces_info_item(self) -> None:
        rec = Receives(source_agent="InputAgent", span=_S)
        old = _spec()
        new = _spec(compositions=(rec,))
        result = self.differ.compare(old, new)
        items = result.by_kind(ChangeKind.COMPOSITION_ADDED)
        assert len(items) == 1
        assert items[0].severity == "info"
        assert "InputAgent" in (items[0].new_value or "")

    def test_composition_removed_produces_breaking_item(self) -> None:
        dlg = Delegates(target_agent="ChildAgent", span=_S)
        old = _spec(compositions=(dlg,))
        new = _spec()
        result = self.differ.compare(old, new)
        items = result.by_kind(ChangeKind.COMPOSITION_REMOVED)
        assert len(items) == 1
        assert items[0].severity == "breaking"

    def test_summary_includes_change_counts(self) -> None:
        old = _spec(
            behaviors=(_behavior("b1", must=(_constraint("safe"),)),),
            invariants=(_invariant("inv1"),),
        )
        new = _spec(behaviors=(_behavior("b2"),))
        result = self.differ.compare(old, new)
        summary = result.summary()
        assert "change" in summary
        assert "breaking" in summary

    def test_to_dict_roundtrip(self) -> None:
        old = _spec()
        new = _spec(behaviors=(_behavior("greet"),))
        result = self.differ.compare(old, new)
        data = result.to_dict()
        assert isinstance(data, dict)
        assert data["total_changes"] >= 1

    def test_multiple_behaviors_complex_diff(self) -> None:
        """Full scenario: 1 behavior removed, 1 added, 1 modified."""
        old = _spec(
            behaviors=(
                _behavior("removed_beh"),
                _behavior("shared_beh", must=(_constraint("old_constraint"),)),
            )
        )
        new = _spec(
            behaviors=(
                _behavior("added_beh"),
                _behavior("shared_beh", must=(_constraint("new_constraint"),)),
            )
        )
        result = self.differ.compare(old, new)
        assert result.has_changes
        assert result.breaking_count >= 1  # removed_beh
        removed_items = result.by_kind(ChangeKind.BEHAVIOR_REMOVED)
        assert any(item.old_value == "removed_beh" for item in removed_items)

    def test_path_prefix_filtering(self) -> None:
        old = _spec(invariants=(_invariant("safety"),))
        new = _spec(
            behaviors=(_behavior("greet"),),
            invariants=(_invariant("security"),),
        )
        result = self.differ.compare(old, new)
        behavior_changes = result.by_path_prefix("behaviors.")
        invariant_changes = result.by_path_prefix("invariants.")
        assert len(behavior_changes) >= 1
        assert len(invariant_changes) >= 1
