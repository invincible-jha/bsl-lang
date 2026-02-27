"""Translation providers for BSL natural-language translation.

Defines the ``TranslationProvider`` protocol plus two built-in
implementations:

- ``MockLLMProvider`` — deterministic mock used in tests; never calls
  a real LLM.
- ``TemplateProvider`` — wraps :class:`~bsl.translate.templates.TemplateTranslator`
  so template-based translation can be used wherever a provider is expected.

Usage
-----
::

    from bsl.translate.providers import MockLLMProvider, TemplateProvider

    provider = MockLLMProvider()
    result = provider.translate("the agent must never leak PII")

    template_provider = TemplateProvider()
    result = template_provider.translate("must always validate input")
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TranslationProvider(Protocol):
    """Protocol for translation back-ends.

    Any callable object (or class with a ``translate`` method) that
    accepts a ``str`` and returns a ``str`` satisfies this protocol.
    The protocol is :func:`runtime-checkable
    <typing.runtime_checkable>` so ``isinstance`` tests work.

    Implementations
    ---------------
    - :class:`MockLLMProvider` — deterministic stub for testing.
    - :class:`TemplateProvider` — wraps the rule-based template engine.
    - Real LLM providers must be injected by callers; this library
      ships no proprietary LLM dependencies.
    """

    def translate(self, text: str) -> str:
        """Translate *text* and return the BSL representation.

        Parameters
        ----------
        text:
            Natural-language constraint description *or* BSL source.

        Returns
        -------
        str
            Translated output text.
        """
        ...  # pragma: no cover


class MockLLMProvider:
    """Deterministic LLM stub for use in unit and CI tests.

    Returns predictable BSL output based on simple prefix matching so
    tests never depend on external network calls or API keys.

    The mapping is intentionally minimal — its purpose is to exercise
    the *plumbing* of :class:`~bsl.translate.nl_to_bsl.NLToBSLTranslator`
    and :class:`~bsl.translate.bsl_to_nl.BSLToNLTranslator`, not to
    produce semantically rich translations.

    Parameters
    ----------
    latency_ms:
        Simulated latency in milliseconds (default 0).  Set to a
        positive value in integration benchmarks.
    """

    def __init__(self, latency_ms: int = 0) -> None:
        self._latency_ms = latency_ms
        self._call_count: int = 0

    def translate(self, text: str) -> str:
        """Return a deterministic mock translation of *text*.

        Parameters
        ----------
        text:
            Input text (NL or BSL).

        Returns
        -------
        str
            Mock translation output.
        """
        import time

        self._call_count += 1
        if self._latency_ms > 0:
            time.sleep(self._latency_ms / 1000.0)

        lowered = text.lower().strip()

        # BSL → NL direction: detect BSL keywords and invert them
        if lowered.startswith("forbid:"):
            body = text[len("FORBID:"):].strip() if text.upper().startswith("FORBID:") else text[7:].strip()
            return f"The agent must never {body}."
        if lowered.startswith("require:"):
            body = text[len("REQUIRE:"):].strip() if text.upper().startswith("REQUIRE:") else text[8:].strip()
            return f"The agent must always {body}."
        if lowered.startswith("recommend:"):
            body = text[len("RECOMMEND:"):].strip() if text.upper().startswith("RECOMMEND:") else text[10:].strip()
            return f"The agent should {body}."
        if lowered.startswith("limit:"):
            body = text[len("LIMIT:"):].strip() if text.upper().startswith("LIMIT:") else text[6:].strip()
            return f"The agent must not exceed {body}."
        if lowered.startswith("deny:"):
            body = text[len("DENY:"):].strip() if text.upper().startswith("DENY:") else text[5:].strip()
            return f"The agent is denied access to {body}."
        if lowered.startswith("allow:"):
            body = text[len("ALLOW:"):].strip() if text.upper().startswith("ALLOW:") else text[6:].strip()
            return f"The agent is permitted to {body}."
        if lowered.startswith("warn:"):
            body = text[len("WARN:"):].strip() if text.upper().startswith("WARN:") else text[5:].strip()
            return f"The agent should warn when {body}."
        if lowered.startswith("audit:"):
            body = text[len("AUDIT:"):].strip() if text.upper().startswith("AUDIT:") else text[6:].strip()
            return f"The agent must audit {body}."
        if lowered.startswith("enforce:"):
            body = text[len("ENFORCE:"):].strip() if text.upper().startswith("ENFORCE:") else text[8:].strip()
            return f"The agent must enforce {body}."
        if lowered.startswith("rate_limit:"):
            body = text[len("RATE_LIMIT:"):].strip() if text.upper().startswith("RATE_LIMIT:") else text[11:].strip()
            return f"The agent must apply rate limiting of {body}."
        if lowered.startswith("timeout:"):
            body = text[len("TIMEOUT:"):].strip() if text.upper().startswith("TIMEOUT:") else text[8:].strip()
            return f"The agent must time out after {body}."
        if lowered.startswith("retry:"):
            body = text[len("RETRY:"):].strip() if text.upper().startswith("RETRY:") else text[6:].strip()
            return f"The agent must retry up to {body}."
        if lowered.startswith("log:"):
            body = text[len("LOG:"):].strip() if text.upper().startswith("LOG:") else text[4:].strip()
            return f"The agent must log {body}."

        # NL → BSL direction: detect common NL patterns.
        # Order: most-specific first so specific phrases are not swallowed by
        # general prefixes (e.g. "must not exceed" before "must not").
        if "must never" in lowered:
            body = _extract_after(text, "must never")
            return f"FORBID: {body}"
        if "must not exceed" in lowered or "cannot exceed" in lowered:
            keyword = "must not exceed" if "must not exceed" in lowered else "cannot exceed"
            body = _extract_after(text, keyword)
            return f"LIMIT: {body}"
        if "must not" in lowered:
            body = _extract_after(text, "must not")
            return f"FORBID: {body}"
        if "must always" in lowered:
            body = _extract_after(text, "must always")
            return f"REQUIRE: {body}"
        if "must" in lowered:
            body = _extract_after(text, "must")
            return f"REQUIRE: {body}"
        if "should" in lowered:
            body = _extract_after(text, "should")
            return f"RECOMMEND: {body}"

        # Fallback: wrap as a generic require
        return f"REQUIRE: {text.strip()}"

    @property
    def call_count(self) -> int:
        """Return the number of times :meth:`translate` has been called."""
        return self._call_count

    def reset_call_count(self) -> None:
        """Reset the call counter to zero."""
        self._call_count = 0


def _extract_after(text: str, keyword: str) -> str:
    """Return the text fragment that follows *keyword* (case-insensitive).

    Parameters
    ----------
    text:
        Source text to search.
    keyword:
        Phrase to search for (case-insensitive).

    Returns
    -------
    str
        Remainder after *keyword*, stripped of leading/trailing
        whitespace.  If *keyword* is not found, returns *text* unchanged.
    """
    lowered = text.lower()
    index = lowered.find(keyword.lower())
    if index == -1:
        return text.strip()
    return text[index + len(keyword):].strip()


class TemplateProvider:
    """Translation provider backed by rule-based template matching.

    This provider wraps :class:`~bsl.translate.templates.TemplateTranslator`
    so it can be passed anywhere a :class:`TranslationProvider` is
    expected.  It never calls an LLM.

    Parameters
    ----------
    fallback_prefix:
        BSL keyword used when no template matches.  Defaults to
        ``"REQUIRE"``.
    """

    def __init__(self, fallback_prefix: str = "REQUIRE") -> None:
        from bsl.translate.templates import TemplateTranslator

        self._translator = TemplateTranslator(fallback_prefix=fallback_prefix)

    def translate(self, text: str) -> str:
        """Translate *text* using the template engine.

        Parameters
        ----------
        text:
            Natural-language constraint description.

        Returns
        -------
        str
            BSL representation.
        """
        return self._translator.translate(text)


__all__ = [
    "TranslationProvider",
    "MockLLMProvider",
    "TemplateProvider",
]
