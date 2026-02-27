"""EU AI Act Article 16 BSL Exporter.

Exports a parsed BSL ``AgentSpec`` AST to a structured EU AI Act
Article 16 documentation package.  The mapping follows the standard
interpretation of Article 16 obligations for high-risk AI systems:

- ``behavior`` blocks   -> Article 16(a) risk management measures
- ``constraint`` blocks -> Article 16(b)/(c) safety requirements
- ``invariant`` blocks  -> Article 16(g) transparency obligations
- ``test`` placeholders -> Article 16(f) validation evidence

This module produces only structural compliance documentation — it does
NOT emit any proprietary scoring, ML weights, or prediction algorithms.

Usage
-----
::

    from bsl.parser.parser import parse
    from bsl.exporters.eu_ai_act import EuAiActExporter

    ast = parse(open("my_agent.bsl").read())
    exporter = EuAiActExporter()
    doc = exporter.export(ast, system_name="MyAgent", risk_level="high")
    print(doc.to_markdown())
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bsl.ast.nodes import AgentSpec, Behavior, Constraint, Invariant

from bsl.exporters.format_helpers import (
    bold,
    bullet_list,
    format_timestamp,
    heading,
    horizontal_rule,
    section,
    table,
)

# ---------------------------------------------------------------------------
# Article 16 reference mapping
# ---------------------------------------------------------------------------

_ARTICLE_16_MAP: dict[str, tuple[str, str]] = {
    "16a": (
        "Article 16(a)",
        "Quality Management System",
    ),
    "16b": (
        "Article 16(b)",
        "Technical Documentation",
    ),
    "16c": (
        "Article 16(c)",
        "Record-Keeping and Logging",
    ),
    "16d": (
        "Article 16(d)",
        "Transparency Information to Users",
    ),
    "16e": (
        "Article 16(e)",
        "Human Oversight Enablement",
    ),
    "16f": (
        "Article 16(f)",
        "Accuracy, Robustness and Cybersecurity",
    ),
    "16g": (
        "Article 16(g)",
        "Conformity Assessment and Registration",
    ),
}

_RISK_LEVEL_LABELS: dict[str, str] = {
    "high": "High-Risk AI System (Annex III)",
    "limited": "Limited-Risk AI System",
    "minimal": "Minimal-Risk AI System",
}


# ---------------------------------------------------------------------------
# Document model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Article16Section:
    """A single Article 16 section in the compliance document.

    Parameters
    ----------
    article_ref:
        Human-readable reference, e.g. ``"Article 16(a)"``.
    title:
        Short title for this section.
    content:
        Narrative content explaining how the BSL spec satisfies this article.
    evidence_refs:
        Tuple of evidence reference strings (behavior/invariant names, etc.).
    """

    article_ref: str
    title: str
    content: str
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dictionary."""
        return {
            "article_ref": self.article_ref,
            "title": self.title,
            "content": self.content,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class EuAiActDocument:
    """A complete EU AI Act Article 16 compliance document.

    Parameters
    ----------
    system_name:
        Name of the AI system being documented.
    risk_level:
        Risk classification: ``"high"``, ``"limited"``, or ``"minimal"``.
    sections:
        Ordered tuple of :class:`Article16Section` items.
    generated_at:
        UTC timestamp of document generation.
    """

    system_name: str
    risk_level: str
    sections: tuple[Article16Section, ...]
    generated_at: datetime

    def to_markdown(self) -> str:
        """Render the document as a Markdown string.

        Returns
        -------
        str
            Multi-section Markdown document.
        """
        risk_label = _RISK_LEVEL_LABELS.get(self.risk_level, self.risk_level.upper())
        parts: list[str] = [
            heading(f"EU AI Act Compliance Documentation — {self.system_name}", 1),
            "",
            f"{bold('Risk Classification:')} {risk_label}",
            f"{bold('Generated:')} {format_timestamp(self.generated_at)}",
            "",
            horizontal_rule(),
            "",
            heading("Executive Summary", 2),
            "",
            (
                f"This document records the Article 16 obligations for the "
                f"{self.system_name} AI system and maps behavioral specifications "
                f"from the BSL source to the relevant regulatory requirements."
            ),
            "",
        ]

        for sec in self.sections:
            parts.append(horizontal_rule())
            parts.append("")
            parts.append(heading(f"{sec.article_ref} — {sec.title}", 2))
            parts.append("")
            parts.append(sec.content)
            if sec.evidence_refs:
                parts.append("")
                parts.append(bold("Evidence References:"))
                parts.append(bullet_list(list(sec.evidence_refs)))
            parts.append("")

        return "\n".join(parts)

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dictionary suitable for JSON export.

        Returns
        -------
        dict[str, object]
            Structured representation of the document.
        """
        return {
            "system_name": self.system_name,
            "risk_level": self.risk_level,
            "generated_at": self.generated_at.isoformat(),
            "sections": [s.to_dict() for s in self.sections],
        }


# ---------------------------------------------------------------------------
# Exporter
# ---------------------------------------------------------------------------


class EuAiActExporter:
    """Exports BSL behavioral specifications to EU AI Act Article 16 documentation.

    The exporter walks the ``AgentSpec`` AST and maps each BSL construct
    to the corresponding Article 16 obligation.

    Mapping
    -------
    - ``behavior`` blocks   -> Article 16(a) quality management / risk measures
    - ``must``/``must_not`` constraints -> Article 16(f) accuracy / robustness
    - ``invariant`` blocks  -> Article 16(g) conformity / transparency obligations
    - Threshold clauses     -> Article 16(f) performance constraints
    """

    def export(
        self,
        bsl_ast: AgentSpec,
        system_name: str,
        risk_level: str = "high",
    ) -> EuAiActDocument:
        """Export a BSL AST to an EU AI Act Article 16 document.

        Parameters
        ----------
        bsl_ast:
            Parsed BSL agent specification.
        system_name:
            Display name for the AI system.
        risk_level:
            Risk classification: ``"high"``, ``"limited"``, or ``"minimal"``.

        Returns
        -------
        EuAiActDocument
            Structured compliance document.
        """
        sections: list[Article16Section] = []

        # Article 16(a) — risk management from behavior blocks
        if bsl_ast.behaviors:
            sections.extend(self._extract_risk_management(bsl_ast))

        # Article 16(b) — technical documentation from all constraints
        sections.append(self._build_technical_documentation(bsl_ast))

        # Article 16(c) — record keeping from audit levels
        sections.append(self._build_record_keeping(bsl_ast))

        # Article 16(d) — transparency from invariant blocks
        if bsl_ast.invariants:
            sections.extend(self._extract_transparency_requirements(bsl_ast))

        # Article 16(e) — human oversight from escalation clauses
        sections.append(self._build_human_oversight(bsl_ast))

        # Article 16(f) — accuracy / robustness from threshold constraints
        sections.append(self._build_accuracy_robustness(bsl_ast))

        # Article 16(g) — conformity assessment / validation evidence
        sections.append(self._build_conformity_assessment(bsl_ast))

        return EuAiActDocument(
            system_name=system_name,
            risk_level=risk_level,
            sections=tuple(sections),
            generated_at=datetime.now(tz=timezone.utc),
        )

    # ------------------------------------------------------------------
    # Public mapping methods
    # ------------------------------------------------------------------

    def _map_behavior_to_article(self, behavior: Behavior) -> Article16Section:
        """Map a single BSL behavior to an Article 16(a) section entry.

        Parameters
        ----------
        behavior:
            BSL behavior node.

        Returns
        -------
        Article16Section
            Populated section with evidence refs to each constraint.
        """
        constraint_count = (
            len(behavior.must_constraints)
            + len(behavior.must_not_constraints)
            + len(behavior.should_constraints)
            + len(behavior.may_constraints)
        )
        evidence_refs: list[str] = [f"behavior:{behavior.name}"]
        for idx in range(len(behavior.must_constraints)):
            evidence_refs.append(f"behavior:{behavior.name}:must:{idx}")
        for idx in range(len(behavior.must_not_constraints)):
            evidence_refs.append(f"behavior:{behavior.name}:must_not:{idx}")

        has_threshold = any(
            t is not None for t in (behavior.confidence, behavior.latency, behavior.cost)
        )
        threshold_note = ""
        if has_threshold:
            thresholds = []
            if behavior.confidence:
                thresholds.append(f"confidence {behavior.confidence.operator} {behavior.confidence.value}")
            if behavior.latency:
                thresholds.append(f"latency {behavior.latency.operator} {behavior.latency.value}")
            if behavior.cost:
                thresholds.append(f"cost {behavior.cost.operator} {behavior.cost.value}")
            threshold_note = f" Performance thresholds: {', '.join(thresholds)}."

        content = (
            f"Behavior '{behavior.name}' defines {constraint_count} behavioral "
            f"constraint(s) governing agent operation.{threshold_note} "
            f"These constraints implement risk management measures as required "
            f"by Article 16(a) to ensure the AI system operates within defined "
            f"safety boundaries."
        )
        return Article16Section(
            article_ref="Article 16(a)",
            title=f"Risk Management — {behavior.name}",
            content=content,
            evidence_refs=tuple(evidence_refs),
        )

    def _extract_safety_constraints(
        self, ast: AgentSpec
    ) -> list[Article16Section]:
        """Extract Article 16(f) safety sections from constraint blocks.

        Parameters
        ----------
        ast:
            Full agent specification.

        Returns
        -------
        list[Article16Section]
            One section per behavior with must_not constraints.
        """
        sections: list[Article16Section] = []
        for behavior in ast.behaviors:
            if not behavior.must_not_constraints:
                continue
            prohibitions = [
                f"behavior:{behavior.name}:must_not:{idx}"
                for idx in range(len(behavior.must_not_constraints))
            ]
            content = (
                f"Behavior '{behavior.name}' defines {len(behavior.must_not_constraints)} "
                f"explicit prohibition(s) preventing unsafe outputs.  These prohibitions "
                f"constitute safety constraints required under Article 16(f) for accuracy "
                f"and robustness assurance."
            )
            sections.append(
                Article16Section(
                    article_ref="Article 16(f)",
                    title=f"Safety Constraints — {behavior.name}",
                    content=content,
                    evidence_refs=tuple(prohibitions),
                )
            )
        return sections

    def _extract_transparency_requirements(
        self, ast: AgentSpec
    ) -> list[Article16Section]:
        """Extract Article 16(d)/(g) transparency sections from invariant blocks.

        Parameters
        ----------
        ast:
            Full agent specification.

        Returns
        -------
        list[Article16Section]
            One section per invariant.
        """
        sections: list[Article16Section] = []
        for invariant in ast.invariants:
            evidence_refs: list[str] = [f"invariant:{invariant.name}"]
            constraint_count = len(invariant.constraints) + len(invariant.prohibitions)
            applies_note = (
                "all behaviors"
                if not invariant.named_behaviors
                else ", ".join(invariant.named_behaviors)
            )
            content = (
                f"Invariant '{invariant.name}' enforces {constraint_count} "
                f"cross-cutting constraint(s) across {applies_note}.  Invariants "
                f"represent transparency obligations under Article 16(g) — they "
                f"guarantee consistent behavioral properties that users and auditors "
                f"can rely upon throughout the system lifecycle."
            )
            sections.append(
                Article16Section(
                    article_ref="Article 16(g)",
                    title=f"Transparency Obligations — {invariant.name}",
                    content=content,
                    evidence_refs=tuple(evidence_refs),
                )
            )
        return sections

    # ------------------------------------------------------------------
    # Internal section builders
    # ------------------------------------------------------------------

    def _extract_risk_management(self, ast: AgentSpec) -> list[Article16Section]:
        """Build Article 16(a) sections for each behavior."""
        return [self._map_behavior_to_article(b) for b in ast.behaviors]

    def _build_technical_documentation(self, ast: AgentSpec) -> Article16Section:
        """Build the Article 16(b) technical documentation section."""
        all_constraints: list[str] = []
        for behavior in ast.behaviors:
            all_constraints.extend(
                f"behavior:{behavior.name}:must:{i}"
                for i in range(len(behavior.must_constraints))
            )
        total_constraints = sum(
            len(b.must_constraints)
            + len(b.must_not_constraints)
            + len(b.should_constraints)
            for b in ast.behaviors
        ) + sum(
            len(inv.constraints) + len(inv.prohibitions)
            for inv in ast.invariants
        )
        agent_meta: list[str] = []
        if ast.version:
            agent_meta.append(f"version {ast.version}")
        if ast.model:
            agent_meta.append(f"model {ast.model}")
        if ast.owner:
            agent_meta.append(f"owner {ast.owner}")
        meta_note = f" ({', '.join(agent_meta)})" if agent_meta else ""

        content = (
            f"Agent '{ast.name}'{meta_note} is documented via {len(ast.behaviors)} "
            f"behavior(s), {len(ast.invariants)} invariant(s), and "
            f"{total_constraints} total constraint(s).  This BSL specification "
            f"constitutes the technical documentation required by Article 16(b) "
            f"for high-risk AI systems."
        )
        return Article16Section(
            article_ref="Article 16(b)",
            title="Technical Documentation",
            content=content,
            evidence_refs=(f"agent:{ast.name}",),
        )

    def _build_record_keeping(self, ast: AgentSpec) -> Article16Section:
        """Build the Article 16(c) record-keeping section."""
        audit_levels = [
            f"behavior:{b.name} (audit:{b.audit.name.lower()})"
            for b in ast.behaviors
        ]
        content = (
            f"The following {len(ast.behaviors)} behavior(s) have audit levels "
            f"configured, supporting Article 16(c) record-keeping requirements: "
            + (", ".join(audit_levels) if audit_levels else "none defined.")
        )
        return Article16Section(
            article_ref="Article 16(c)",
            title="Record-Keeping and Logging",
            content=content,
            evidence_refs=tuple(f"behavior:{b.name}:audit" for b in ast.behaviors),
        )

    def _build_human_oversight(self, ast: AgentSpec) -> Article16Section:
        """Build the Article 16(e) human oversight section."""
        escalation_behaviors = [b.name for b in ast.behaviors if b.escalation is not None]
        if escalation_behaviors:
            content = (
                f"Human oversight (escalate_to_human) is configured for "
                f"{len(escalation_behaviors)} behavior(s): "
                f"{', '.join(escalation_behaviors)}.  These escalation clauses "
                f"implement Article 16(e) requirements enabling human intervention "
                f"when automated decision-making reaches defined boundaries."
            )
            evidence = tuple(f"behavior:{name}:escalation" for name in escalation_behaviors)
        else:
            content = (
                "No explicit escalation-to-human clauses are defined in this specification.  "
                "Operators must document alternative human oversight mechanisms to satisfy "
                "Article 16(e) requirements."
            )
            evidence = ()
        return Article16Section(
            article_ref="Article 16(e)",
            title="Human Oversight Enablement",
            content=content,
            evidence_refs=evidence,
        )

    def _build_accuracy_robustness(self, ast: AgentSpec) -> Article16Section:
        """Build the Article 16(f) accuracy and robustness section."""
        threshold_refs: list[str] = []
        details: list[str] = []
        for behavior in ast.behaviors:
            if behavior.confidence:
                threshold_refs.append(f"behavior:{behavior.name}:confidence")
                details.append(
                    f"{behavior.name}: confidence {behavior.confidence.operator} "
                    f"{behavior.confidence.value}"
                    f"{'%' if behavior.confidence.is_percentage else ''}"
                )
            if behavior.latency:
                threshold_refs.append(f"behavior:{behavior.name}:latency")
                details.append(f"{behavior.name}: latency {behavior.latency.operator} {behavior.latency.value}")
            if behavior.cost:
                threshold_refs.append(f"behavior:{behavior.name}:cost")
                details.append(f"{behavior.name}: cost {behavior.cost.operator} {behavior.cost.value}")

        safety_constraint_count = sum(len(b.must_not_constraints) for b in ast.behaviors)

        if details:
            threshold_note = (
                f"Performance thresholds defined: {'; '.join(details)}.  "
            )
        else:
            threshold_note = "No numeric performance thresholds are defined.  "

        content = (
            threshold_note
            + f"Safety prohibitions (must_not): {safety_constraint_count}.  "
            + "These constraints satisfy Article 16(f) accuracy, robustness, and "
            + "cybersecurity obligations."
        )
        return Article16Section(
            article_ref="Article 16(f)",
            title="Accuracy, Robustness and Cybersecurity",
            content=content,
            evidence_refs=tuple(threshold_refs),
        )

    def _build_conformity_assessment(self, ast: AgentSpec) -> Article16Section:
        """Build the Article 16(g) conformity assessment section."""
        test_evidence: list[str] = []
        for behavior in ast.behaviors:
            for idx in range(len(behavior.must_constraints)):
                test_evidence.append(f"test:behavior:{behavior.name}:must:{idx}")
        for invariant in ast.invariants:
            for idx in range(len(invariant.constraints)):
                test_evidence.append(f"test:invariant:{invariant.name}:must:{idx}")

        content = (
            f"The BSL specification for '{ast.name}' provides "
            f"{len(test_evidence)} machine-verifiable constraint(s) that can be "
            f"compiled into automated test cases.  These constitute conformity "
            f"assessment evidence as required by Article 16(g).  Compile this "
            f"specification with the BSL pytest target to generate runnable "
            f"validation tests."
        )
        return Article16Section(
            article_ref="Article 16(g)",
            title="Conformity Assessment and Validation Evidence",
            content=content,
            evidence_refs=tuple(test_evidence[:20]),  # cap evidence list length
        )


__all__ = [
    "Article16Section",
    "EuAiActDocument",
    "EuAiActExporter",
]
