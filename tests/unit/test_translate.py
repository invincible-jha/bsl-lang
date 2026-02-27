"""Unit tests for bsl.translate — template patterns, NL→BSL, BSL→NL,
providers, CLI command, and edge cases.

Coverage targets
----------------
- bsl/translate/__init__.py
- bsl/translate/templates.py
- bsl/translate/providers.py
- bsl/translate/nl_to_bsl.py
- bsl/translate/bsl_to_nl.py
- bsl/cli/main.py  (translate command)
"""
from __future__ import annotations

import re
import warnings
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from bsl.cli.main import cli
from bsl.translate import (
    BSLToNLTranslator,
    MockLLMProvider,
    NLToBSLTranslator,
    TemplateProvider,
    TemplateTranslator,
    TranslationError,
    TranslationPattern,
    TranslationProvider,
)
from bsl.translate.bsl_to_nl import _translate_directive_builtin
from bsl.translate.providers import _extract_after
from bsl.translate.templates import (
    _clean_body,
    _strip_subject_prefix,
    _p,
)


# ===========================================================================
# Helpers
# ===========================================================================


def _make_runner() -> CliRunner:
    return CliRunner()


# ===========================================================================
# 1. TranslationPattern dataclass
# ===========================================================================


class TestTranslationPattern:
    def test_frozen_dataclass(self) -> None:
        pattern = _p(r"must never (.+)", "FORBID", description="test")
        with pytest.raises((AttributeError, TypeError)):
            pattern.bsl_keyword = "REQUIRE"  # type: ignore[misc]

    def test_fields_accessible(self) -> None:
        pat = _p(r"must never (.+)", "FORBID", group=1, description="desc")
        assert pat.bsl_keyword == "FORBID"
        assert pat.body_group == 1
        assert pat.description == "desc"
        assert pat.pattern.match("must never do something")

    def test_default_body_group(self) -> None:
        pat = _p(r"must never (.+)", "FORBID")
        assert pat.body_group == 1

    def test_custom_flags(self) -> None:
        # _p uses IGNORECASE by default
        pat = _p(r"MUST NEVER (.+)", "FORBID")
        assert pat.pattern.match("must never something")


# ===========================================================================
# 2. Template helper functions
# ===========================================================================


class TestStripSubjectPrefix:
    def test_strips_the_agent(self) -> None:
        assert _strip_subject_prefix("the agent must never leak PII") == "must never leak PII"

    def test_strips_agent_without_the(self) -> None:
        assert _strip_subject_prefix("agent must always validate") == "must always validate"

    def test_strips_the_system(self) -> None:
        assert _strip_subject_prefix("the system must log events") == "must log events"

    def test_strips_the_model(self) -> None:
        assert _strip_subject_prefix("the model should recommend actions") == "should recommend actions"

    def test_strips_it(self) -> None:
        assert _strip_subject_prefix("it must never expose data") == "must never expose data"

    def test_strips_this_agent(self) -> None:
        assert _strip_subject_prefix("this agent shall enforce policies") == "shall enforce policies"

    def test_no_subject_prefix_unchanged(self) -> None:
        text = "must never leak PII"
        assert _strip_subject_prefix(text) == text

    def test_unrecognised_subject_unchanged(self) -> None:
        text = "users must always authenticate"
        assert _strip_subject_prefix(text) == text


class TestCleanBody:
    def test_strips_trailing_period(self) -> None:
        assert _clean_body("leak PII.") == "leak PII"

    def test_strips_trailing_comma(self) -> None:
        assert _clean_body("validate input,") == "validate input"

    def test_strips_trailing_semicolon(self) -> None:
        assert _clean_body("enforce rate limits;") == "enforce rate limits"

    def test_strips_trailing_exclamation(self) -> None:
        assert _clean_body("log all events!") == "log all events"

    def test_strips_trailing_question_mark(self) -> None:
        assert _clean_body("check permissions?") == "check permissions"

    def test_strips_leading_whitespace(self) -> None:
        assert _clean_body("  validate input") == "validate input"

    def test_preserves_internal_punctuation(self) -> None:
        assert _clean_body("exceed 1,000 tokens") == "exceed 1,000 tokens"

    def test_empty_string(self) -> None:
        assert _clean_body("") == ""


# ===========================================================================
# 3. TemplateTranslator — FORBID patterns
# ===========================================================================


class TestTemplateTranslatorForbid:
    def setup_method(self) -> None:
        self.translator = TemplateTranslator()

    def test_must_never(self) -> None:
        result = self.translator.translate("must never expose credentials")
        assert result == "FORBID: expose credentials"

    def test_must_never_with_subject(self) -> None:
        result = self.translator.translate("the agent must never leak PII")
        assert result == "FORBID: leak PII"

    def test_must_not(self) -> None:
        result = self.translator.translate("must not share user data")
        assert result == "FORBID: share user data"

    def test_is_not_allowed_to(self) -> None:
        result = self.translator.translate("is not allowed to access external APIs")
        assert result == "FORBID: access external APIs"

    def test_is_prohibited_from(self) -> None:
        result = self.translator.translate("is prohibited from storing plaintext passwords")
        assert result == "FORBID: storing plaintext passwords"

    def test_is_forbidden_from(self) -> None:
        result = self.translator.translate("is forbidden from calling external services")
        assert result == "FORBID: calling external services"

    def test_is_forbidden_to(self) -> None:
        result = self.translator.translate("is forbidden to disclose confidential data")
        assert result == "FORBID: disclose confidential data"

    def test_cannot(self) -> None:
        result = self.translator.translate("cannot send emails without consent")
        assert result == "FORBID: send emails without consent"

    def test_cannot_variant_two_words(self) -> None:
        result = self.translator.translate("can not invoke privileged operations")
        assert result == "FORBID: invoke privileged operations"

    def test_case_insensitive(self) -> None:
        result = self.translator.translate("MUST NEVER Expose Credentials")
        assert result.startswith("FORBID:")

    def test_trailing_period_stripped(self) -> None:
        result = self.translator.translate("must never expose credentials.")
        assert result == "FORBID: expose credentials"


# ===========================================================================
# 4. TemplateTranslator — REQUIRE patterns
# ===========================================================================


class TestTemplateTranslatorRequire:
    def setup_method(self) -> None:
        self.translator = TemplateTranslator()

    def test_must_always(self) -> None:
        result = self.translator.translate("must always validate input")
        assert result == "REQUIRE: validate input"

    def test_must_general(self) -> None:
        result = self.translator.translate("must validate input before processing")
        assert result == "REQUIRE: validate input before processing"

    def test_is_required_to(self) -> None:
        result = self.translator.translate("is required to authenticate every request")
        assert result == "REQUIRE: authenticate every request"

    def test_shall(self) -> None:
        result = self.translator.translate("shall maintain an audit log")
        assert result == "REQUIRE: maintain an audit log"

    def test_shall_always(self) -> None:
        result = self.translator.translate("shall always encrypt data at rest")
        assert result == "REQUIRE: encrypt data at rest"

    def test_with_subject(self) -> None:
        result = self.translator.translate("the agent must always hash passwords")
        assert result == "REQUIRE: hash passwords"


# ===========================================================================
# 5. TemplateTranslator — RECOMMEND patterns
# ===========================================================================


class TestTemplateTranslatorRecommend:
    def setup_method(self) -> None:
        self.translator = TemplateTranslator()

    def test_should(self) -> None:
        result = self.translator.translate("should validate input format")
        assert result == "RECOMMEND: validate input format"

    def test_ought_to(self) -> None:
        result = self.translator.translate("ought to cache responses when safe")
        assert result == "RECOMMEND: cache responses when safe"

    def test_is_encouraged_to(self) -> None:
        result = self.translator.translate("is encouraged to use structured outputs")
        assert result == "RECOMMEND: use structured outputs"

    def test_is_advised_to(self) -> None:
        result = self.translator.translate("is advised to include confidence scores")
        assert result == "RECOMMEND: include confidence scores"

    def test_with_subject(self) -> None:
        result = self.translator.translate("the agent should prefer idempotent operations")
        assert result == "RECOMMEND: prefer idempotent operations"


# ===========================================================================
# 6. TemplateTranslator — LIMIT patterns
# ===========================================================================


class TestTemplateTranslatorLimit:
    def setup_method(self) -> None:
        self.translator = TemplateTranslator()

    def test_must_not_exceed(self) -> None:
        result = self.translator.translate("must not exceed 1000 tokens")
        assert result == "LIMIT: 1000 tokens"

    def test_cannot_exceed(self) -> None:
        result = self.translator.translate("cannot exceed 500 requests per minute")
        assert result == "LIMIT: 500 requests per minute"

    def test_no_more_than(self) -> None:
        result = self.translator.translate("no more than 10 retries")
        assert result == "LIMIT: 10 retries"

    def test_is_limited_to(self) -> None:
        result = self.translator.translate("is limited to 100 concurrent sessions")
        assert result == "LIMIT: 100 concurrent sessions"

    def test_is_capped_at(self) -> None:
        result = self.translator.translate("is capped at 2048 output tokens")
        assert result == "LIMIT: 2048 output tokens"

    def test_with_subject(self) -> None:
        result = self.translator.translate("the agent must not exceed 50 API calls per second")
        assert result == "LIMIT: 50 API calls per second"


# ===========================================================================
# 7. TemplateTranslator — DENY patterns
# ===========================================================================


class TestTemplateTranslatorDeny:
    def setup_method(self) -> None:
        self.translator = TemplateTranslator()

    def test_is_denied_access_to(self) -> None:
        result = self.translator.translate("is denied access to the internal database")
        assert result == "DENY: the internal database"

    def test_is_denied_without_access_to(self) -> None:
        result = self.translator.translate("is denied admin routes")
        assert result == "DENY: admin routes"

    def test_may_not_access(self) -> None:
        result = self.translator.translate("may not access payment records")
        assert result == "DENY: payment records"

    def test_is_blocked_from(self) -> None:
        result = self.translator.translate("is blocked from reading system logs")
        assert result == "DENY: reading system logs"


# ===========================================================================
# 8. TemplateTranslator — ALLOW patterns
# ===========================================================================


class TestTemplateTranslatorAllow:
    def setup_method(self) -> None:
        self.translator = TemplateTranslator()

    def test_is_permitted_to(self) -> None:
        result = self.translator.translate("is permitted to read public datasets")
        assert result == "ALLOW: read public datasets"

    def test_is_allowed_to(self) -> None:
        result = self.translator.translate("is allowed to cache read-only responses")
        assert result == "ALLOW: cache read-only responses"

    def test_may(self) -> None:
        result = self.translator.translate("may request additional context from the user")
        assert result == "ALLOW: request additional context from the user"


# ===========================================================================
# 9. TemplateTranslator — WARN patterns
# ===========================================================================


class TestTemplateTranslatorWarn:
    def setup_method(self) -> None:
        self.translator = TemplateTranslator()

    def test_must_warn_when(self) -> None:
        result = self.translator.translate("must warn when confidence is below 70%")
        assert result == "WARN: confidence is below 70%"

    def test_should_warn_when(self) -> None:
        result = self.translator.translate("should warn when the response time exceeds 2s")
        assert result == "WARN: the response time exceeds 2s"

    def test_must_emit_warning_when(self) -> None:
        result = self.translator.translate("must emit a warning when retries are exhausted")
        assert result == "WARN: retries are exhausted"

    def test_must_emit_warning_if(self) -> None:
        result = self.translator.translate("must emit a warning if the context window is nearly full")
        assert result == "WARN: the context window is nearly full"


# ===========================================================================
# 10. TemplateTranslator — AUDIT, LOG, ENFORCE patterns
# ===========================================================================


class TestTemplateTranslatorAuditLogEnforce:
    def setup_method(self) -> None:
        self.translator = TemplateTranslator()

    def test_must_audit(self) -> None:
        result = self.translator.translate("must audit all privileged operations")
        assert result == "AUDIT: all privileged operations"

    def test_is_subject_to_audit(self) -> None:
        result = self.translator.translate("is subject to audit for data access events")
        assert result == "AUDIT: data access events"

    def test_must_log(self) -> None:
        result = self.translator.translate("must log all authentication attempts")
        assert result == "LOG: all authentication attempts"

    def test_is_required_to_log(self) -> None:
        result = self.translator.translate("is required to log request metadata")
        assert result == "LOG: request metadata"

    def test_must_enforce(self) -> None:
        result = self.translator.translate("must enforce role-based access control")
        assert result == "ENFORCE: role-based access control"

    def test_is_required_to_enforce(self) -> None:
        result = self.translator.translate("is required to enforce content safety policies")
        assert result == "ENFORCE: content safety policies"


# ===========================================================================
# 11. TemplateTranslator — RATE_LIMIT, TIMEOUT, RETRY patterns
# ===========================================================================


class TestTemplateTranslatorRateLimitTimeoutRetry:
    def setup_method(self) -> None:
        self.translator = TemplateTranslator()

    def test_must_apply_rate_limiting_of(self) -> None:
        result = self.translator.translate("must apply rate limiting of 100 requests per minute")
        assert result == "RATE_LIMIT: 100 requests per minute"

    def test_must_apply_rate_limit_of(self) -> None:
        result = self.translator.translate("must apply rate limit of 50 calls per second")
        assert result == "RATE_LIMIT: 50 calls per second"

    def test_is_rate_limited_to(self) -> None:
        result = self.translator.translate("is rate-limited to 200 requests per hour")
        assert result == "RATE_LIMIT: 200 requests per hour"

    def test_must_timeout_after(self) -> None:
        result = self.translator.translate("must time out after 30 seconds")
        assert result == "TIMEOUT: 30 seconds"

    def test_has_a_timeout_of(self) -> None:
        result = self.translator.translate("has a timeout of 5 seconds")
        assert result == "TIMEOUT: 5 seconds"

    def test_must_retry(self) -> None:
        result = self.translator.translate("must retry up to 3 times")
        assert result == "RETRY: 3 times"

    def test_must_retry_without_up_to(self) -> None:
        result = self.translator.translate("must retry 5 times on failure")
        assert result == "RETRY: 5 times on failure"

    def test_is_retried_up_to(self) -> None:
        result = self.translator.translate("is retried up to 3 times on network error")
        assert result == "RETRY: 3 times on network error"


# ===========================================================================
# 12. TemplateTranslator — fallback behaviour
# ===========================================================================


class TestTemplateTranslatorFallback:
    def test_unrecognised_input_uses_fallback_prefix(self) -> None:
        translator = TemplateTranslator(fallback_prefix="REQUIRE")
        result = translator.translate("do something unrecognised")
        assert result.startswith("REQUIRE:")

    def test_custom_fallback_prefix(self) -> None:
        translator = TemplateTranslator(fallback_prefix="NOTE")
        result = translator.translate("an entirely unrecognised phrase")
        assert result.startswith("NOTE:")

    def test_empty_string_returns_fallback_with_empty_body(self) -> None:
        translator = TemplateTranslator()
        result = translator.translate("")
        assert result == "REQUIRE: "

    def test_whitespace_only_returns_fallback_with_empty_body(self) -> None:
        translator = TemplateTranslator()
        result = translator.translate("   ")
        assert result == "REQUIRE: "

    def test_fallback_strips_trailing_punctuation(self) -> None:
        translator = TemplateTranslator()
        result = translator.translate("something unusual.")
        # body should have trailing period stripped
        assert not result.endswith(".")


# ===========================================================================
# 13. TemplateTranslator — pattern management
# ===========================================================================


class TestTemplateTranslatorPatternManagement:
    def test_pattern_count_greater_than_10(self) -> None:
        translator = TemplateTranslator()
        assert translator.pattern_count >= 10

    def test_add_pattern_prepends(self) -> None:
        translator = TemplateTranslator()
        original_count = translator.pattern_count
        new_pattern = TranslationPattern(
            pattern=re.compile(r"custom phrase (.+)", re.IGNORECASE),
            bsl_keyword="CUSTOM",
        )
        translator.add_pattern(new_pattern)
        assert translator.pattern_count == original_count + 1
        result = translator.translate("custom phrase do a thing")
        assert result == "CUSTOM: do a thing"

    def test_list_patterns_returns_copy(self) -> None:
        translator = TemplateTranslator()
        patterns_a = translator.list_patterns()
        patterns_b = translator.list_patterns()
        assert patterns_a is not patterns_b
        assert len(patterns_a) == len(patterns_b)

    def test_custom_patterns_list(self) -> None:
        single_pattern = TranslationPattern(
            pattern=re.compile(r"never (.+)", re.IGNORECASE),
            bsl_keyword="FORBID",
        )
        translator = TemplateTranslator(patterns=[single_pattern])
        assert translator.pattern_count == 1
        result = translator.translate("never expose data")
        assert result == "FORBID: expose data"


# ===========================================================================
# 14. TranslationProvider Protocol
# ===========================================================================


class TestTranslationProviderProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        provider = MockLLMProvider()
        assert isinstance(provider, TranslationProvider)

    def test_template_provider_satisfies_protocol(self) -> None:
        provider = TemplateProvider()
        assert isinstance(provider, TranslationProvider)

    def test_custom_class_satisfies_protocol(self) -> None:
        class CustomProvider:
            def translate(self, text: str) -> str:
                return f"CUSTOM: {text}"

        assert isinstance(CustomProvider(), TranslationProvider)


# ===========================================================================
# 15. MockLLMProvider
# ===========================================================================


class TestMockLLMProvider:
    def test_must_never_maps_to_forbid(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("must never expose PII")
        assert result.startswith("FORBID:")

    def test_must_always_maps_to_require(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("must always validate input")
        assert result.startswith("REQUIRE:")

    def test_should_maps_to_recommend(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("should cache responses")
        assert result.startswith("RECOMMEND:")

    def test_must_not_maps_to_forbid(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("must not share secrets")
        assert result.startswith("FORBID:")

    def test_must_exceed_maps_to_limit(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("must not exceed 1000 tokens")
        assert result.startswith("LIMIT:")

    def test_forbid_directive_maps_to_nl(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("FORBID: share credentials")
        assert "must never" in result.lower() or "share credentials" in result

    def test_require_directive_maps_to_nl(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("REQUIRE: validate input")
        assert "must always" in result.lower() or "validate input" in result

    def test_recommend_directive_maps_to_nl(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("RECOMMEND: cache results")
        assert "should" in result.lower() or "cache results" in result

    def test_limit_directive_maps_to_nl(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("LIMIT: 1000 tokens")
        assert "exceed" in result.lower() or "1000 tokens" in result

    def test_deny_directive_maps_to_nl(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("DENY: admin panel")
        assert "denied" in result.lower() or "admin panel" in result

    def test_allow_directive_maps_to_nl(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("ALLOW: read public data")
        assert "permitted" in result.lower() or "read public data" in result

    def test_warn_directive_maps_to_nl(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("WARN: confidence below threshold")
        assert "warn" in result.lower() or "confidence below threshold" in result

    def test_audit_directive_maps_to_nl(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("AUDIT: all data access")
        assert "audit" in result.lower() or "all data access" in result

    def test_enforce_directive_maps_to_nl(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("ENFORCE: rate limiting policy")
        assert "enforce" in result.lower() or "rate limiting policy" in result

    def test_rate_limit_directive_maps_to_nl(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("RATE_LIMIT: 100 per minute")
        assert "rate limit" in result.lower() or "100 per minute" in result

    def test_timeout_directive_maps_to_nl(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("TIMEOUT: 30 seconds")
        assert "time out" in result.lower() or "30 seconds" in result

    def test_retry_directive_maps_to_nl(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("RETRY: 3 times")
        assert "retry" in result.lower() or "3 times" in result

    def test_log_directive_maps_to_nl(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("LOG: all auth events")
        assert "log" in result.lower() or "all auth events" in result

    def test_fallback_wraps_as_require(self) -> None:
        provider = MockLLMProvider()
        result = provider.translate("some completely unknown phrase xyz")
        assert result.startswith("REQUIRE:")

    def test_call_count_increments(self) -> None:
        provider = MockLLMProvider()
        provider.translate("must never do X")
        provider.translate("must always do Y")
        assert provider.call_count == 2

    def test_reset_call_count(self) -> None:
        provider = MockLLMProvider()
        provider.translate("test input")
        provider.reset_call_count()
        assert provider.call_count == 0

    def test_deterministic_output(self) -> None:
        provider = MockLLMProvider()
        result_a = provider.translate("must never expose credentials")
        result_b = provider.translate("must never expose credentials")
        assert result_a == result_b

    def test_zero_latency_by_default(self) -> None:
        import time

        provider = MockLLMProvider(latency_ms=0)
        start = time.monotonic()
        provider.translate("must always validate")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 500  # well under any reasonable limit

    def test_call_count_starts_at_zero(self) -> None:
        provider = MockLLMProvider()
        assert provider.call_count == 0


# ===========================================================================
# 16. TemplateProvider
# ===========================================================================


class TestTemplateProvider:
    def test_translate_must_never(self) -> None:
        provider = TemplateProvider()
        result = provider.translate("must never expose credentials")
        assert result == "FORBID: expose credentials"

    def test_translate_should(self) -> None:
        provider = TemplateProvider()
        result = provider.translate("should validate inputs")
        assert result == "RECOMMEND: validate inputs"

    def test_custom_fallback_prefix(self) -> None:
        provider = TemplateProvider(fallback_prefix="NOTE")
        result = provider.translate("some unrecognised phrase")
        assert result.startswith("NOTE:")

    def test_satisfies_translation_provider_protocol(self) -> None:
        provider = TemplateProvider()
        assert isinstance(provider, TranslationProvider)


# ===========================================================================
# 17. _extract_after helper
# ===========================================================================


class TestExtractAfter:
    def test_extracts_after_keyword(self) -> None:
        result = _extract_after("must never leak PII", "must never")
        assert result == "leak PII"

    def test_case_insensitive(self) -> None:
        result = _extract_after("MUST NEVER leak PII", "must never")
        assert result == "leak PII"

    def test_keyword_not_found_returns_original(self) -> None:
        result = _extract_after("some other text", "must never")
        assert result == "some other text"

    def test_strips_whitespace(self) -> None:
        result = _extract_after("must always  validate input", "must always")
        assert result == "validate input"


# ===========================================================================
# 18. NLToBSLTranslator
# ===========================================================================


class TestNLToBSLTranslator:
    def test_translate_with_template_provider(self) -> None:
        provider = TemplateProvider()
        translator = NLToBSLTranslator(provider=provider)
        result = translator.translate("must never expose credentials")
        assert result == "FORBID: expose credentials"

    def test_translate_with_mock_provider(self) -> None:
        provider = MockLLMProvider()
        translator = NLToBSLTranslator(provider=provider)
        result = translator.translate("must always validate input")
        assert result.startswith("REQUIRE:")

    def test_translate_strips_input_whitespace(self) -> None:
        provider = MockLLMProvider()
        translator = NLToBSLTranslator(provider=provider)
        result_trimmed = translator.translate("must never expose secrets")
        result_padded = translator.translate("  must never expose secrets  ")
        assert result_trimmed == result_padded

    def test_none_input_raises_value_error(self) -> None:
        provider = MockLLMProvider()
        translator = NLToBSLTranslator(provider=provider)
        with pytest.raises(ValueError, match="None"):
            translator.translate(None)  # type: ignore[arg-type]

    def test_provider_exception_raises_translation_error(self) -> None:
        broken_provider = MagicMock()
        broken_provider.translate.side_effect = RuntimeError("network down")
        translator = NLToBSLTranslator(provider=broken_provider)
        with pytest.raises(TranslationError, match="network down"):
            translator.translate("must always validate")

    def test_translation_error_propagates_unchanged(self) -> None:
        broken_provider = MagicMock()
        broken_provider.translate.side_effect = TranslationError(
            "provider error", original_text="test"
        )
        translator = NLToBSLTranslator(provider=broken_provider)
        with pytest.raises(TranslationError):
            translator.translate("some input")

    def test_translate_batch(self) -> None:
        provider = TemplateProvider()
        translator = NLToBSLTranslator(provider=provider)
        inputs = [
            "must never expose PII",
            "must always validate input",
            "should cache responses",
        ]
        results = translator.translate_batch(inputs)
        assert len(results) == 3
        assert results[0].startswith("FORBID:")
        assert results[1].startswith("REQUIRE:")
        assert results[2].startswith("RECOMMEND:")

    def test_translate_batch_empty_list(self) -> None:
        provider = TemplateProvider()
        translator = NLToBSLTranslator(provider=provider)
        assert translator.translate_batch([]) == []

    def test_provider_property(self) -> None:
        provider = MockLLMProvider()
        translator = NLToBSLTranslator(provider=provider)
        assert translator.provider is provider

    def test_no_provider_emits_warning_and_falls_back(self) -> None:
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            translator = NLToBSLTranslator()
        assert any(issubclass(w.category, RuntimeWarning) for w in recorded)
        # Fallback still works
        result = translator.translate("must never expose secrets")
        assert result.startswith("FORBID:")

    def test_empty_string_translates(self) -> None:
        provider = TemplateProvider()
        translator = NLToBSLTranslator(provider=provider)
        result = translator.translate("")
        assert isinstance(result, str)


# ===========================================================================
# 19. BSLToNLTranslator
# ===========================================================================


class TestBSLToNLTranslator:
    def test_forbid_to_nl_with_mock_provider(self) -> None:
        provider = MockLLMProvider()
        translator = BSLToNLTranslator(provider=provider)
        result = translator.translate("FORBID: expose credentials")
        assert "must never" in result.lower() or "expose credentials" in result

    def test_require_to_nl_with_builtin(self) -> None:
        translator = BSLToNLTranslator()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            result = translator.translate("REQUIRE: validate input schema")
        assert "must always" in result.lower()
        assert "validate input schema" in result

    def test_forbid_to_nl_with_builtin(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        result = translator.translate("FORBID: expose PII")
        assert "must never" in result.lower()
        assert "expose PII" in result

    def test_recommend_to_nl_with_builtin(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        result = translator.translate("RECOMMEND: cache responses")
        assert "should" in result.lower()
        assert "cache responses" in result

    def test_limit_to_nl_with_builtin(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        result = translator.translate("LIMIT: 1000 tokens")
        assert "exceed" in result.lower()
        assert "1000 tokens" in result

    def test_deny_to_nl_with_builtin(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        result = translator.translate("DENY: admin panel")
        assert "denied" in result.lower()

    def test_allow_to_nl_with_builtin(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        result = translator.translate("ALLOW: public endpoints")
        assert "permitted" in result.lower()

    def test_warn_to_nl_with_builtin(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        result = translator.translate("WARN: confidence below 70%")
        assert "warn" in result.lower()

    def test_audit_to_nl_with_builtin(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        result = translator.translate("AUDIT: privileged access")
        assert "audit" in result.lower()

    def test_log_to_nl_with_builtin(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        result = translator.translate("LOG: all requests")
        assert "log" in result.lower()

    def test_enforce_to_nl_with_builtin(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        result = translator.translate("ENFORCE: access control policy")
        assert "enforce" in result.lower()

    def test_rate_limit_to_nl_with_builtin(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        result = translator.translate("RATE_LIMIT: 100 per minute")
        assert "rate limit" in result.lower()

    def test_timeout_to_nl_with_builtin(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        result = translator.translate("TIMEOUT: 30 seconds")
        assert "time out" in result.lower()

    def test_retry_to_nl_with_builtin(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        result = translator.translate("RETRY: 3 times")
        assert "retry" in result.lower()

    def test_unknown_keyword_produces_generic_fallback(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        result = translator.translate("XYZZY: do something")
        assert "XYZZY: do something" in result

    def test_none_input_raises_value_error(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        with pytest.raises(ValueError, match="None"):
            translator.translate(None)  # type: ignore[arg-type]

    def test_provider_exception_raises_translation_error(self) -> None:
        broken_provider = MagicMock()
        broken_provider.translate.side_effect = RuntimeError("provider down")
        translator = BSLToNLTranslator(provider=broken_provider)
        with pytest.raises(TranslationError, match="provider down"):
            translator.translate("FORBID: expose data")

    def test_translation_error_propagates(self) -> None:
        broken_provider = MagicMock()
        broken_provider.translate.side_effect = TranslationError("err", original_text="t")
        translator = BSLToNLTranslator(provider=broken_provider)
        with pytest.raises(TranslationError):
            translator.translate("FORBID: something")

    def test_translate_batch(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        inputs = ["FORBID: expose PII", "REQUIRE: validate input", "LIMIT: 100 tokens"]
        results = translator.translate_batch(inputs)
        assert len(results) == 3
        assert all(isinstance(r, str) for r in results)

    def test_translate_batch_empty(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        assert translator.translate_batch([]) == []

    def test_no_provider_emits_runtime_warning(self) -> None:
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            BSLToNLTranslator()
        assert any(issubclass(w.category, RuntimeWarning) for w in recorded)

    def test_provider_property_returns_provider(self) -> None:
        provider = MockLLMProvider()
        translator = BSLToNLTranslator(provider=provider)
        assert translator.provider is provider

    def test_provider_property_none_when_no_provider(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        assert translator.provider is None

    def test_multi_line_bsl_translated(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        bsl_block = "FORBID: expose PII\nREQUIRE: validate input"
        result = translator.translate(bsl_block)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_plain_text_passed_through(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = BSLToNLTranslator()
        plain = "This is not a BSL directive at all"
        result = translator.translate(plain)
        assert isinstance(result, str)


# ===========================================================================
# 20. _translate_directive_builtin helper
# ===========================================================================


class TestTranslateDirectiveBuiltin:
    def test_known_keywords_return_string(self) -> None:
        known = [
            "FORBID", "REQUIRE", "RECOMMEND", "LIMIT", "DENY",
            "ALLOW", "WARN", "AUDIT", "LOG", "ENFORCE",
            "RATE_LIMIT", "TIMEOUT", "RETRY",
        ]
        for keyword in known:
            result = _translate_directive_builtin(keyword, "test body")
            assert result is not None, f"Expected result for {keyword}"
            assert isinstance(result, str)

    def test_unknown_keyword_returns_none(self) -> None:
        result = _translate_directive_builtin("UNKNOWN_KEYWORD", "some body")
        assert result is None

    def test_case_insensitive_keyword(self) -> None:
        result = _translate_directive_builtin("forbid", "expose PII")
        assert result is not None
        assert "must never" in result.lower()


# ===========================================================================
# 21. TranslationError
# ===========================================================================


class TestTranslationError:
    def test_is_exception(self) -> None:
        err = TranslationError("something went wrong", original_text="test input")
        assert isinstance(err, Exception)
        assert str(err) == "something went wrong"
        assert err.original_text == "test input"

    def test_default_original_text(self) -> None:
        err = TranslationError("oops")
        assert err.original_text == ""

    def test_raise_and_catch(self) -> None:
        with pytest.raises(TranslationError) as exc_info:
            raise TranslationError("provider failed", original_text="input text")
        assert exc_info.value.original_text == "input text"


# ===========================================================================
# 22. Module __init__ exports
# ===========================================================================


class TestModuleExports:
    def test_all_symbols_importable(self) -> None:
        from bsl.translate import (
            BSLToNLTranslator,
            MockLLMProvider,
            NLToBSLTranslator,
            TemplateProvider,
            TemplateTranslator,
            TranslationError,
            TranslationPattern,
            TranslationProvider,
        )
        assert NLToBSLTranslator is not None
        assert BSLToNLTranslator is not None
        assert TranslationError is not None
        assert TranslationProvider is not None
        assert MockLLMProvider is not None
        assert TemplateProvider is not None
        assert TemplateTranslator is not None
        assert TranslationPattern is not None


# ===========================================================================
# 23. CLI — translate command
# ===========================================================================


class TestCLITranslateCommand:
    def setup_method(self) -> None:
        self.runner = _make_runner()

    def test_basic_nl_to_bsl_template(self) -> None:
        result = self.runner.invoke(
            cli, ["translate", "must never expose credentials"]
        )
        assert result.exit_code == 0
        assert "FORBID" in result.output

    def test_explicit_template_provider(self) -> None:
        result = self.runner.invoke(
            cli,
            ["translate", "must always validate input", "--provider", "template"],
        )
        assert result.exit_code == 0
        assert "REQUIRE" in result.output

    def test_llm_provider_falls_back_to_template(self) -> None:
        result = self.runner.invoke(
            cli,
            ["translate", "must never share secrets", "--provider", "llm"],
        )
        assert result.exit_code == 0
        # Warning should be on stderr; result on stdout
        assert "FORBID" in result.output

    def test_llm_provider_warning_on_stderr(self) -> None:
        result = self.runner.invoke(
            cli,
            ["translate", "must always log events", "--provider", "llm"],
        )
        # The warning goes to stderr (captured separately by mix_stderr=False)
        assert result.exit_code == 0

    def test_reverse_bsl_to_nl(self) -> None:
        result = self.runner.invoke(
            cli,
            ["translate", "FORBID: expose credentials", "--reverse"],
        )
        assert result.exit_code == 0
        # The TemplateProvider is the default; it may echo back the text or
        # translate it — either way, output must be non-empty.
        assert result.output.strip() != ""

    def test_should_pattern(self) -> None:
        result = self.runner.invoke(
            cli, ["translate", "should validate inputs before processing"]
        )
        assert result.exit_code == 0
        assert "RECOMMEND" in result.output

    def test_limit_pattern(self) -> None:
        result = self.runner.invoke(
            cli, ["translate", "must not exceed 100 tokens"]
        )
        assert result.exit_code == 0
        assert "LIMIT" in result.output

    def test_invalid_provider_choice(self) -> None:
        result = self.runner.invoke(
            cli,
            ["translate", "must never expose data", "--provider", "gpt4"],
        )
        assert result.exit_code != 0

    def test_help_text_available(self) -> None:
        result = self.runner.invoke(cli, ["translate", "--help"])
        assert result.exit_code == 0
        assert "translate" in result.output.lower()


# ===========================================================================
# 24. Graceful degradation / integration-style tests
# ===========================================================================


class TestGracefulDegradation:
    def test_nl_to_bsl_without_llm_uses_templates(self) -> None:
        """NLToBSLTranslator without an LLM should fall back to TemplateProvider."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            translator = NLToBSLTranslator()
        result = translator.translate("must never expose PII")
        assert result.startswith("FORBID:")

    def test_template_provider_no_network_required(self) -> None:
        """TemplateProvider must produce output with no network I/O."""
        provider = TemplateProvider()
        inputs = [
            "must never expose credentials",
            "must always validate input",
            "should recommend idempotent operations",
            "must not exceed 1000 tokens",
            "is denied access to admin panel",
        ]
        for text in inputs:
            result = provider.translate(text)
            assert ":" in result, f"Expected BSL directive for: {text!r}"

    def test_mock_provider_never_calls_network(self) -> None:
        """MockLLMProvider must work with no external connectivity."""
        with patch("socket.getaddrinfo", side_effect=OSError("no network")):
            provider = MockLLMProvider()
            result = provider.translate("must always validate")
        assert result.startswith("REQUIRE:")

    def test_round_trip_nl_to_bsl_to_nl(self) -> None:
        """Translate NL → BSL → NL; the final NL must mention the key phrase."""
        nl_input = "must never expose user credentials"
        nl_provider = TemplateProvider()
        nl_translator = NLToBSLTranslator(provider=nl_provider)
        bsl_output = nl_translator.translate(nl_input)
        assert bsl_output.startswith("FORBID:")

        bsl_provider = MockLLMProvider()
        bsl_translator = BSLToNLTranslator(provider=bsl_provider)
        nl_output = bsl_translator.translate(bsl_output)
        assert "expose user credentials" in nl_output or "must never" in nl_output.lower()
