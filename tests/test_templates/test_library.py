"""Tests for bsl.templates — TemplateLibrary and built-in templates."""
from __future__ import annotations

import pytest

from bsl.templates.library import TemplateLibrary, TemplateMetadata


# ===========================================================================
# TemplateMetadata
# ===========================================================================


class TestTemplateMetadata:
    def test_frozen(self) -> None:
        meta = TemplateMetadata(
            name="test", domain="test", description="A test template"
        )
        with pytest.raises((AttributeError, TypeError)):
            meta.name = "other"  # type: ignore[misc]

    def test_defaults(self) -> None:
        meta = TemplateMetadata(name="x", domain="y", description="z")
        assert meta.tags == ()
        assert meta.version == "1.0"

    def test_tags_tuple(self) -> None:
        meta = TemplateMetadata(
            name="x", domain="y", description="z", tags=("a", "b")
        )
        assert meta.tags == ("a", "b")


# ===========================================================================
# TemplateLibrary — initialization
# ===========================================================================


class TestTemplateLibraryInit:
    def test_auto_load_builtins(self) -> None:
        lib = TemplateLibrary()
        assert len(lib) >= 20

    def test_no_builtins_empty(self) -> None:
        lib = TemplateLibrary(auto_load_builtins=False)
        assert len(lib) == 0

    def test_contains_operator(self) -> None:
        lib = TemplateLibrary()
        assert "healthcare" in lib
        assert "nonexistent_template_xyz" not in lib

    def test_len(self) -> None:
        lib = TemplateLibrary()
        assert len(lib) >= 20


# ===========================================================================
# load_template
# ===========================================================================


class TestLoadTemplate:
    def setup_method(self) -> None:
        self.lib = TemplateLibrary()

    def test_load_healthcare(self) -> None:
        source = self.lib.load_template("healthcare")
        assert "HealthcareAssistant" in source

    def test_load_finance(self) -> None:
        source = self.lib.load_template("finance")
        assert "FinanceAdvisor" in source

    def test_load_customer_service(self) -> None:
        source = self.lib.load_template("customer_service")
        assert "CustomerServiceAgent" in source

    def test_load_code_review(self) -> None:
        source = self.lib.load_template("code_review")
        assert "CodeReviewAgent" in source

    def test_load_research_assistant(self) -> None:
        source = self.lib.load_template("research_assistant")
        assert "ResearchAssistant" in source

    def test_load_content_moderation(self) -> None:
        source = self.lib.load_template("content_moderation")
        assert "ContentModerationAgent" in source

    def test_load_data_analyst(self) -> None:
        source = self.lib.load_template("data_analyst")
        assert "DataAnalystAgent" in source

    def test_load_legal(self) -> None:
        source = self.lib.load_template("legal")
        assert "LegalResearchAgent" in source

    def test_load_education(self) -> None:
        source = self.lib.load_template("education")
        assert "EducationTutor" in source

    def test_load_cybersecurity(self) -> None:
        source = self.lib.load_template("cybersecurity")
        assert "CybersecurityAdvisor" in source

    def test_load_fraud_detection(self) -> None:
        source = self.lib.load_template("fraud_detection")
        assert "FraudDetectionAgent" in source

    def test_load_nonexistent_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="nonexistent"):
            self.lib.load_template("nonexistent")

    def test_load_returns_string(self) -> None:
        source = self.lib.load_template("healthcare")
        assert isinstance(source, str)
        assert len(source) > 0


# ===========================================================================
# get_metadata
# ===========================================================================


class TestGetMetadata:
    def setup_method(self) -> None:
        self.lib = TemplateLibrary()

    def test_get_metadata_healthcare(self) -> None:
        meta = self.lib.get_metadata("healthcare")
        assert meta.name == "healthcare"
        assert meta.domain == "healthcare"
        assert "hipaa" in meta.tags

    def test_get_metadata_nonexistent_raises(self) -> None:
        with pytest.raises(KeyError):
            self.lib.get_metadata("nonexistent")

    def test_metadata_has_description(self) -> None:
        meta = self.lib.get_metadata("finance")
        assert len(meta.description) > 0


# ===========================================================================
# list_templates
# ===========================================================================


class TestListTemplates:
    def setup_method(self) -> None:
        self.lib = TemplateLibrary()

    def test_returns_list_of_metadata(self) -> None:
        templates = self.lib.list_templates()
        assert isinstance(templates, list)
        assert all(isinstance(t, TemplateMetadata) for t in templates)

    def test_sorted_alphabetically(self) -> None:
        templates = self.lib.list_templates()
        names = [t.name for t in templates]
        assert names == sorted(names)

    def test_all_builtins_present(self) -> None:
        lib = TemplateLibrary()
        names = lib.list_names()
        expected = [
            "accessibility_assistant",
            "code_review",
            "content_moderation",
            "customer_service",
            "cybersecurity",
            "data_analyst",
            "devops_assistant",
            "document_processing",
            "ecommerce_advisor",
            "education",
            "finance",
            "fraud_detection",
            "healthcare",
            "hr_assistant",
            "legal",
            "manufacturing_qa",
            "marketing_content",
            "mental_health_support",
            "research_assistant",
            "sales_assistant",
            "supply_chain",
            "travel_assistant",
        ]
        for expected_name in expected:
            assert expected_name in names, f"Missing template: {expected_name}"

    def test_count_at_least_20(self) -> None:
        templates = self.lib.list_templates()
        assert len(templates) >= 20


# ===========================================================================
# list_names
# ===========================================================================


class TestListNames:
    def test_returns_sorted_list(self) -> None:
        lib = TemplateLibrary()
        names = lib.list_names()
        assert names == sorted(names)

    def test_includes_healthcare(self) -> None:
        lib = TemplateLibrary()
        assert "healthcare" in lib.list_names()


# ===========================================================================
# list_by_domain
# ===========================================================================


class TestListByDomain:
    def setup_method(self) -> None:
        self.lib = TemplateLibrary()

    def test_list_healthcare_domain(self) -> None:
        templates = self.lib.list_by_domain("healthcare")
        assert len(templates) >= 1
        assert all(t.domain == "healthcare" for t in templates)

    def test_list_finance_domain(self) -> None:
        templates = self.lib.list_by_domain("finance")
        assert len(templates) >= 1

    def test_case_insensitive(self) -> None:
        lower = self.lib.list_by_domain("healthcare")
        upper = self.lib.list_by_domain("HEALTHCARE")
        assert lower == upper

    def test_unknown_domain_empty(self) -> None:
        templates = self.lib.list_by_domain("xyzzy_nonexistent")
        assert templates == []


# ===========================================================================
# search_by_tag
# ===========================================================================


class TestSearchByTag:
    def setup_method(self) -> None:
        self.lib = TemplateLibrary()

    def test_search_by_tag_safety(self) -> None:
        templates = self.lib.search_by_tag("safety")
        assert len(templates) >= 1

    def test_search_by_tag_hipaa(self) -> None:
        templates = self.lib.search_by_tag("hipaa")
        assert any(t.name == "healthcare" for t in templates)

    def test_case_insensitive_tag(self) -> None:
        lower = self.lib.search_by_tag("security")
        upper = self.lib.search_by_tag("SECURITY")
        assert lower == upper

    def test_unknown_tag_empty(self) -> None:
        templates = self.lib.search_by_tag("tag_that_does_not_exist_xyz")
        assert templates == []


# ===========================================================================
# register
# ===========================================================================


class TestRegister:
    def setup_method(self) -> None:
        self.lib = TemplateLibrary(auto_load_builtins=False)

    def test_register_and_load(self) -> None:
        self.lib.register(
            name="custom_domain",
            source="agent MyAgent { }",
            domain="custom",
            description="A custom agent",
        )
        assert "custom_domain" in self.lib
        source = self.lib.load_template("custom_domain")
        assert "MyAgent" in source

    def test_register_duplicate_raises(self) -> None:
        self.lib.register(name="dup", source="agent A { }")
        with pytest.raises(ValueError, match="already registered"):
            self.lib.register(name="dup", source="agent B { }")

    def test_register_overwrite(self) -> None:
        self.lib.register(name="dup", source="agent A { }")
        self.lib.register(name="dup", source="agent B { }", overwrite=True)
        source = self.lib.load_template("dup")
        assert "agent B" in source

    def test_register_with_tags(self) -> None:
        self.lib.register(
            name="tagged",
            source="agent T { }",
            tags=("alpha", "beta"),
        )
        meta = self.lib.get_metadata("tagged")
        assert "alpha" in meta.tags

    def test_register_custom_version(self) -> None:
        self.lib.register(name="versioned", source="agent V { }", version="2.5")
        meta = self.lib.get_metadata("versioned")
        assert meta.version == "2.5"

    def test_registered_template_appears_in_list(self) -> None:
        self.lib.register(name="new_one", source="agent N { }", description="desc")
        names = self.lib.list_names()
        assert "new_one" in names
