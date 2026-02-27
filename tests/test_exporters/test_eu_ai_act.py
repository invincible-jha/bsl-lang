"""Tests for bsl.exporters.eu_ai_act — EU AI Act Article 16 exporter."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from bsl.ast.nodes import AgentSpec
from bsl.exporters.eu_ai_act import Article16Section, EuAiActDocument, EuAiActExporter
from bsl.parser.parser import parse

# ---------------------------------------------------------------------------
# BSL fixtures
# ---------------------------------------------------------------------------

_FULL_AGENT_BSL = """\
agent CustomerServiceAgent {
    version: "2.0"
    model: "gpt-4o"
    owner: "support-team"
    behavior greet {
        must: response
        must_not: expose_pii
        confidence: >= 95%
        latency: < 500
        audit: full_trace
        escalate_to_human when: confidence < 0.5
    }
    behavior search {
        must: query_validated
        must_not: leak_credentials
        cost: < 10
    }
    invariant privacy {
        applies_to: all_behaviors
        severity: critical
        must_not: share_user_data
    }
    invariant accuracy {
        applies_to: [greet]
        severity: high
        must: response contains "verified"
    }
}
"""

_MINIMAL_AGENT_BSL = """\
agent MinimalAgent {
    behavior action {
        must: valid_output
    }
}
"""

_NO_BEHAVIORS_BSL = """\
agent StaticAgent {
    version: "0.1"
    invariant always {
        must: safe
    }
}
"""


@pytest.fixture()
def full_ast() -> AgentSpec:
    return parse(_FULL_AGENT_BSL)


@pytest.fixture()
def minimal_ast() -> AgentSpec:
    return parse(_MINIMAL_AGENT_BSL)


@pytest.fixture()
def no_behaviors_ast() -> AgentSpec:
    return parse(_NO_BEHAVIORS_BSL)


@pytest.fixture()
def exporter() -> EuAiActExporter:
    return EuAiActExporter()


# ---------------------------------------------------------------------------
# Article16Section tests
# ---------------------------------------------------------------------------


class TestArticle16Section:
    def test_frozen_dataclass(self) -> None:
        sec = Article16Section(
            article_ref="Article 16(a)",
            title="Test",
            content="Some content",
            evidence_refs=("ref1",),
        )
        with pytest.raises((AttributeError, TypeError)):
            sec.article_ref = "changed"  # type: ignore[misc]

    def test_to_dict_structure(self) -> None:
        sec = Article16Section(
            article_ref="Article 16(a)",
            title="Risk Mgmt",
            content="Content here",
            evidence_refs=("behavior:greet", "behavior:search"),
        )
        result = sec.to_dict()
        assert result["article_ref"] == "Article 16(a)"
        assert result["title"] == "Risk Mgmt"
        assert result["content"] == "Content here"
        assert result["evidence_refs"] == ["behavior:greet", "behavior:search"]

    def test_to_dict_empty_evidence_refs(self) -> None:
        sec = Article16Section(
            article_ref="Article 16(b)",
            title="Docs",
            content="Technical docs",
            evidence_refs=(),
        )
        result = sec.to_dict()
        assert result["evidence_refs"] == []


# ---------------------------------------------------------------------------
# EuAiActDocument tests
# ---------------------------------------------------------------------------


class TestEuAiActDocument:
    def test_frozen_dataclass(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "MySystem")
        with pytest.raises((AttributeError, TypeError)):
            doc.system_name = "changed"  # type: ignore[misc]

    def test_to_dict_has_required_keys(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "TestSystem", risk_level="high")
        result = doc.to_dict()
        assert "system_name" in result
        assert "risk_level" in result
        assert "generated_at" in result
        assert "sections" in result

    def test_to_dict_system_name(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "TargetSystem")
        result = doc.to_dict()
        assert result["system_name"] == "TargetSystem"

    def test_to_dict_risk_level(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S", risk_level="limited")
        assert doc.to_dict()["risk_level"] == "limited"

    def test_to_dict_sections_is_list(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S")
        assert isinstance(doc.to_dict()["sections"], list)

    def test_to_dict_is_json_serializable(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "JSONSystem")
        json_str = json.dumps(doc.to_dict())
        assert len(json_str) > 0

    def test_to_markdown_returns_string(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "MarkdownSystem")
        md = doc.to_markdown()
        assert isinstance(md, str)
        assert len(md) > 0

    def test_to_markdown_contains_system_name(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "CustomerServiceAgent")
        md = doc.to_markdown()
        assert "CustomerServiceAgent" in md

    def test_to_markdown_contains_article_refs(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S")
        md = doc.to_markdown()
        assert "Article 16" in md

    def test_to_markdown_contains_risk_level(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S", risk_level="high")
        md = doc.to_markdown()
        assert "High-Risk" in md or "high" in md.lower()

    def test_to_markdown_has_headings(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S")
        md = doc.to_markdown()
        assert md.count("#") >= 2  # at least title + one section


# ---------------------------------------------------------------------------
# EuAiActExporter.export tests
# ---------------------------------------------------------------------------


class TestEuAiActExporter:
    def test_export_returns_document(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "TestSystem")
        assert isinstance(doc, EuAiActDocument)

    def test_export_system_name_set(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "MyAISystem")
        assert doc.system_name == "MyAISystem"

    def test_export_default_risk_level_high(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S")
        assert doc.risk_level == "high"

    def test_export_custom_risk_level(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S", risk_level="minimal")
        assert doc.risk_level == "minimal"

    def test_export_generated_at_is_utc(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S")
        assert doc.generated_at.tzinfo is not None

    def test_export_has_sections(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S")
        assert len(doc.sections) > 0

    def test_export_article_16a_present(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S")
        refs = {s.article_ref for s in doc.sections}
        assert "Article 16(a)" in refs

    def test_export_article_16b_present(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S")
        refs = {s.article_ref for s in doc.sections}
        assert "Article 16(b)" in refs

    def test_export_article_16c_present(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S")
        refs = {s.article_ref for s in doc.sections}
        assert "Article 16(c)" in refs

    def test_export_article_16e_present(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S")
        refs = {s.article_ref for s in doc.sections}
        assert "Article 16(e)" in refs

    def test_export_article_16f_present(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S")
        refs = {s.article_ref for s in doc.sections}
        assert "Article 16(f)" in refs

    def test_export_article_16g_present(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S")
        refs = {s.article_ref for s in doc.sections}
        assert "Article 16(g)" in refs

    def test_export_minimal_agent(self, minimal_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(minimal_ast, "Minimal")
        assert doc.system_name == "Minimal"
        assert len(doc.sections) > 0

    def test_export_no_behaviors_agent(
        self, no_behaviors_ast: AgentSpec, exporter: EuAiActExporter
    ) -> None:
        doc = exporter.export(no_behaviors_ast, "Static")
        assert doc is not None
        # No Article 16(a) sections for behaviors when there are none
        behavior_sections = [s for s in doc.sections if "Risk Management" in s.title]
        assert len(behavior_sections) == 0

    def test_behavior_sections_match_behavior_count(
        self, full_ast: AgentSpec, exporter: EuAiActExporter
    ) -> None:
        doc = exporter.export(full_ast, "S")
        behavior_sections = [s for s in doc.sections if s.article_ref == "Article 16(a)"]
        assert len(behavior_sections) == len(full_ast.behaviors)

    def test_invariant_sections_match_invariant_count(
        self, full_ast: AgentSpec, exporter: EuAiActExporter
    ) -> None:
        doc = exporter.export(full_ast, "S")
        inv_sections = [s for s in doc.sections if "Transparency Obligations" in s.title]
        assert len(inv_sections) == len(full_ast.invariants)

    def test_escalation_section_mentions_behavior(
        self, full_ast: AgentSpec, exporter: EuAiActExporter
    ) -> None:
        doc = exporter.export(full_ast, "S")
        oversight_sections = [s for s in doc.sections if s.article_ref == "Article 16(e)"]
        assert len(oversight_sections) == 1
        assert "greet" in oversight_sections[0].content

    def test_threshold_section_mentions_confidence(
        self, full_ast: AgentSpec, exporter: EuAiActExporter
    ) -> None:
        doc = exporter.export(full_ast, "S")
        robustness_sections = [s for s in doc.sections if s.article_ref == "Article 16(f)"]
        assert len(robustness_sections) == 1
        assert "confidence" in robustness_sections[0].content.lower()

    def test_map_behavior_to_article_returns_section(
        self, full_ast: AgentSpec, exporter: EuAiActExporter
    ) -> None:
        behavior = full_ast.behaviors[0]
        section = exporter._map_behavior_to_article(behavior)
        assert isinstance(section, Article16Section)
        assert section.article_ref == "Article 16(a)"

    def test_extract_safety_constraints_returns_list(
        self, full_ast: AgentSpec, exporter: EuAiActExporter
    ) -> None:
        sections = exporter._extract_safety_constraints(full_ast)
        assert isinstance(sections, list)

    def test_extract_transparency_requirements_returns_list(
        self, full_ast: AgentSpec, exporter: EuAiActExporter
    ) -> None:
        sections = exporter._extract_transparency_requirements(full_ast)
        assert isinstance(sections, list)
        assert len(sections) == len(full_ast.invariants)

    def test_evidence_refs_are_tuples(self, full_ast: AgentSpec, exporter: EuAiActExporter) -> None:
        doc = exporter.export(full_ast, "S")
        for sec in doc.sections:
            assert isinstance(sec.evidence_refs, tuple)
