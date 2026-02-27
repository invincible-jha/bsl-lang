"""Rule-based template translator for common NL → BSL patterns.

This module translates natural-language constraint descriptions into BSL
directives using regular-expression patterns.  It has **zero LLM
dependency** and is suitable for offline use and CI environments.

Supported patterns
------------------

+--------------------------------+---------------------------+
| Natural-language phrase        | BSL output                |
+================================+===========================+
| "must never X"                 | ``FORBID: X``             |
+--------------------------------+---------------------------+
| "must not X"                   | ``FORBID: X``             |
+--------------------------------+---------------------------+
| "is not allowed to X"          | ``FORBID: X``             |
+--------------------------------+---------------------------+
| "is prohibited from X"         | ``FORBID: X``             |
+--------------------------------+---------------------------+
| "must always Y"                | ``REQUIRE: Y``            |
+--------------------------------+---------------------------+
| "must Y" (no never/always)     | ``REQUIRE: Y``            |
+--------------------------------+---------------------------+
| "is required to Y"             | ``REQUIRE: Y``            |
+--------------------------------+---------------------------+
| "shall Y"                      | ``REQUIRE: Y``            |
+--------------------------------+---------------------------+
| "should X"                     | ``RECOMMEND: X``          |
+--------------------------------+---------------------------+
| "ought to X"                   | ``RECOMMEND: X``          |
+--------------------------------+---------------------------+
| "is encouraged to X"           | ``RECOMMEND: X``          |
+--------------------------------+---------------------------+
| "must not exceed N"            | ``LIMIT: N``              |
+--------------------------------+---------------------------+
| "cannot exceed N"              | ``LIMIT: N``              |
+--------------------------------+---------------------------+
| "no more than N"               | ``LIMIT: N``              |
+--------------------------------+---------------------------+
| "is denied access to R"        | ``DENY: R``               |
+--------------------------------+---------------------------+
| "may not access R"             | ``DENY: R``               |
+--------------------------------+---------------------------+
| "is permitted to X"            | ``ALLOW: X``              |
+--------------------------------+---------------------------+
| "may X"                        | ``ALLOW: X``              |
+--------------------------------+---------------------------+
| "must warn when C"             | ``WARN: C``               |
+--------------------------------+---------------------------+
| "should warn when C"           | ``WARN: C``               |
+--------------------------------+---------------------------+
| "must audit X"                 | ``AUDIT: X``              |
+--------------------------------+---------------------------+
| "must log X"                   | ``LOG: X``                |
+--------------------------------+---------------------------+
| "must enforce X"               | ``ENFORCE: X``            |
+--------------------------------+---------------------------+
| "must apply rate limiting of N"| ``RATE_LIMIT: N``         |
+--------------------------------+---------------------------+
| "must time out after N"        | ``TIMEOUT: N``            |
+--------------------------------+---------------------------+
| "must retry up to N"           | ``RETRY: N``              |
+--------------------------------+---------------------------+

Usage
-----
::

    from bsl.translate.templates import TemplateTranslator

    translator = TemplateTranslator()
    print(translator.translate("must never leak PII"))
    # FORBID: leak PII
    print(translator.translate("must not exceed 1000 tokens"))
    # LIMIT: 1000 tokens
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class TranslationPattern:
    """A single NL → BSL translation rule.

    Parameters
    ----------
    pattern:
        Compiled regular expression.  Must define at least one capture
        group whose concatenation forms the BSL body.
    bsl_keyword:
        The BSL directive keyword (e.g. ``"FORBID"``, ``"REQUIRE"``).
    body_group:
        Index of the capture group that contains the BSL body text.
        Defaults to 1.
    description:
        Human-readable description used in documentation and error
        messages.
    """

    pattern: re.Pattern[str]
    bsl_keyword: str
    body_group: int = 1
    description: str = ""


def _p(
    regex: str,
    keyword: str,
    *,
    group: int = 1,
    description: str = "",
    flags: int = re.IGNORECASE,
) -> TranslationPattern:
    """Convenience factory for :class:`TranslationPattern`."""
    return TranslationPattern(
        pattern=re.compile(regex, flags),
        bsl_keyword=keyword,
        body_group=group,
        description=description,
    )


# ---------------------------------------------------------------------------
# Pattern definitions
#
# ORDERING IS CRITICAL: more-specific patterns MUST appear before more-general
# ones that share a common prefix (e.g. "must audit" before "must (.+)").
#
# General principle:
#   1. Patterns with the most words / tightest match go first.
#   2. Catch-all patterns for a given leading keyword go last.
# ---------------------------------------------------------------------------

_DEFAULT_PATTERNS: list[TranslationPattern] = [
    # ── LIMIT (before FORBID "must not" catch-all & "cannot" catch-all) ──────
    _p(
        r"must\s+not\s+exceed\s+(.+)",
        "LIMIT",
        description="'must not exceed N' → LIMIT: N",
    ),
    _p(
        r"(?:cannot|can\s+not)\s+exceed\s+(.+)",
        "LIMIT",
        description="'cannot exceed N' → LIMIT: N",
    ),
    _p(
        r"no\s+more\s+than\s+(.+)",
        "LIMIT",
        description="'no more than N' → LIMIT: N",
    ),
    _p(
        r"(?:is|are)\s+limited\s+to\s+(.+)",
        "LIMIT",
        description="'is limited to N' → LIMIT: N",
    ),
    _p(
        r"(?:is|are)\s+capped\s+at\s+(.+)",
        "LIMIT",
        description="'is capped at N' → LIMIT: N",
    ),
    # ── WARN (before "must (.+)" and "should (.+)" catch-alls) ───────────────
    _p(
        r"(?:must|should)\s+warn\s+(?:the\s+user\s+)?when\s+(.+)",
        "WARN",
        description="'must/should warn when C' → WARN: C",
    ),
    _p(
        r"(?:must|should)\s+emit\s+(?:a\s+)?warning\s+(?:when|if)\s+(.+)",
        "WARN",
        description="'must emit a warning when C' → WARN: C",
    ),
    # ── AUDIT (before "must (.+)" catch-all) ─────────────────────────────────
    _p(
        r"must\s+audit\s+(.+)",
        "AUDIT",
        description="'must audit X' → AUDIT: X",
    ),
    _p(
        r"(?:is|are)\s+subject\s+to\s+audit\s+(?:for\s+)?(.+)",
        "AUDIT",
        description="'is subject to audit for X' → AUDIT: X",
    ),
    # ── LOG (before "must (.+)" and "is required to (.+)" catch-alls) ────────
    _p(
        r"must\s+log\s+(.+)",
        "LOG",
        description="'must log X' → LOG: X",
    ),
    _p(
        r"(?:is|are)\s+required\s+to\s+log\s+(.+)",
        "LOG",
        description="'is required to log X' → LOG: X",
    ),
    # ── ENFORCE (before "must (.+)" and "is required to (.+)" catch-alls) ────
    _p(
        r"must\s+enforce\s+(.+)",
        "ENFORCE",
        description="'must enforce X' → ENFORCE: X",
    ),
    _p(
        r"(?:is|are)\s+required\s+to\s+enforce\s+(.+)",
        "ENFORCE",
        description="'is required to enforce X' → ENFORCE: X",
    ),
    # ── RATE_LIMIT (before "must (.+)" catch-all) ────────────────────────────
    _p(
        r"must\s+apply\s+rate\s+limit(?:ing)?\s+of\s+(.+)",
        "RATE_LIMIT",
        description="'must apply rate limiting of N' → RATE_LIMIT: N",
    ),
    _p(
        r"(?:is|are)\s+rate[- ]?limited\s+to\s+(.+)",
        "RATE_LIMIT",
        description="'is rate-limited to N' → RATE_LIMIT: N",
    ),
    # ── TIMEOUT (before "must (.+)" catch-all) ───────────────────────────────
    _p(
        r"must\s+time\s*out\s+after\s+(.+)",
        "TIMEOUT",
        description="'must time out after N' → TIMEOUT: N",
    ),
    _p(
        r"has\s+a\s+timeout\s+of\s+(.+)",
        "TIMEOUT",
        description="'has a timeout of N' → TIMEOUT: N",
    ),
    # ── RETRY (before "must (.+)" catch-all) ─────────────────────────────────
    _p(
        r"must\s+retry\s+(?:up\s+to\s+)?(.+)",
        "RETRY",
        description="'must retry up to N' → RETRY: N",
    ),
    _p(
        r"(?:is|are)\s+retried\s+(?:up\s+to\s+)?(.+)",
        "RETRY",
        description="'is retried up to N' → RETRY: N",
    ),
    # ── FORBID ───────────────────────────────────────────────────────────────
    _p(
        r"must\s+never\s+(.+)",
        "FORBID",
        description="'must never X' → FORBID: X",
    ),
    _p(
        r"must\s+not\s+(.+)",
        "FORBID",
        description="'must not X' (after LIMIT patterns) → FORBID: X",
    ),
    _p(
        r"(?:is|are)\s+not\s+allowed\s+to\s+(.+)",
        "FORBID",
        description="'is not allowed to X' → FORBID: X",
    ),
    _p(
        r"(?:is|are)\s+prohibited\s+from\s+(.+)",
        "FORBID",
        description="'is prohibited from X' → FORBID: X",
    ),
    _p(
        r"(?:is|are)\s+forbidden\s+(?:from\s+|to\s+)?(.+)",
        "FORBID",
        description="'is forbidden from/to X' → FORBID: X",
    ),
    _p(
        r"(?:cannot|can\s+not)\s+(.+)",
        "FORBID",
        description="'cannot X' (after LIMIT 'cannot exceed') → FORBID: X",
    ),
    # ── REQUIRE ──────────────────────────────────────────────────────────────
    _p(
        r"must\s+always\s+(.+)",
        "REQUIRE",
        description="'must always Y' → REQUIRE: Y",
    ),
    _p(
        r"(?:is|are)\s+required\s+to\s+(.+)",
        "REQUIRE",
        description="'is required to Y' (general, after LOG/ENFORCE) → REQUIRE: Y",
    ),
    _p(
        r"shall\s+(?:always\s+)?(.+)",
        "REQUIRE",
        description="'shall Y' → REQUIRE: Y",
    ),
    _p(
        r"must\s+(.+)",
        "REQUIRE",
        description="'must Y' (general catch-all, after all specific must-* patterns) → REQUIRE: Y",
    ),
    # ── RECOMMEND ────────────────────────────────────────────────────────────
    _p(
        r"ought\s+to\s+(.+)",
        "RECOMMEND",
        description="'ought to X' → RECOMMEND: X",
    ),
    _p(
        r"(?:is|are)\s+encouraged\s+to\s+(.+)",
        "RECOMMEND",
        description="'is encouraged to X' → RECOMMEND: X",
    ),
    _p(
        r"(?:is|are)\s+advised\s+to\s+(.+)",
        "RECOMMEND",
        description="'is advised to X' → RECOMMEND: X",
    ),
    _p(
        r"should\s+(.+)",
        "RECOMMEND",
        description="'should X' (general, after WARN patterns) → RECOMMEND: X",
    ),
    # ── DENY ─────────────────────────────────────────────────────────────────
    _p(
        r"(?:is|are)\s+denied\s+(?:access\s+to\s+)?(.+)",
        "DENY",
        description="'is denied access to R' → DENY: R",
    ),
    _p(
        r"may\s+not\s+access\s+(.+)",
        "DENY",
        description="'may not access R' → DENY: R",
    ),
    _p(
        r"(?:is|are)\s+blocked\s+from\s+(.+)",
        "DENY",
        description="'is blocked from R' → DENY: R",
    ),
    # ── ALLOW ────────────────────────────────────────────────────────────────
    _p(
        r"(?:is|are)\s+permitted\s+to\s+(.+)",
        "ALLOW",
        description="'is permitted to X' → ALLOW: X",
    ),
    _p(
        r"(?:is|are)\s+allowed\s+to\s+(.+)",
        "ALLOW",
        description="'is allowed to X' → ALLOW: X",
    ),
    _p(
        r"may\s+(.+)",
        "ALLOW",
        description="'may X' → ALLOW: X",
    ),
]


def _strip_subject_prefix(text: str) -> str:
    """Remove common leading subject phrases such as 'the agent' or 'it'.

    Parameters
    ----------
    text:
        Input sentence.

    Returns
    -------
    str
        Text with leading subject phrase stripped, or the original text
        if no subject prefix is recognised.
    """
    subject_patterns = [
        r"^(?:the\s+)?agent\s+",
        r"^(?:the\s+)?system\s+",
        r"^(?:the\s+)?model\s+",
        r"^it\s+",
        r"^this\s+agent\s+",
    ]
    for sub_pattern in subject_patterns:
        result = re.sub(sub_pattern, "", text, count=1, flags=re.IGNORECASE)
        if result != text:
            return result
    return text


def _clean_body(text: str) -> str:
    """Strip trailing punctuation from a BSL body string.

    Parameters
    ----------
    text:
        Captured body text.

    Returns
    -------
    str
        Cleaned body without trailing ``.,;:!?`` characters.
    """
    return text.strip().rstrip(".,;:!?").strip()


class TemplateTranslator:
    """Rule-based NL → BSL translator.

    Translates natural-language constraint descriptions into BSL
    directives using a prioritised list of regular-expression patterns.
    No LLM or network access is required.

    Parameters
    ----------
    patterns:
        List of :class:`TranslationPattern` objects.  When ``None``,
        the built-in :data:`_DEFAULT_PATTERNS` list is used.
    fallback_prefix:
        BSL keyword emitted when no pattern matches.  Defaults to
        ``"REQUIRE"``.

    Examples
    --------
    ::

        translator = TemplateTranslator()
        translator.translate("must never expose credentials")
        # 'FORBID: expose credentials'
        translator.translate("should validate input format")
        # 'RECOMMEND: validate input format'
    """

    def __init__(
        self,
        patterns: list[TranslationPattern] | None = None,
        fallback_prefix: str = "REQUIRE",
    ) -> None:
        self._patterns: list[TranslationPattern] = (
            patterns if patterns is not None else list(_DEFAULT_PATTERNS)
        )
        self._fallback_prefix = fallback_prefix

    def translate(self, text: str) -> str:
        """Translate *text* from natural language to BSL.

        Parameters
        ----------
        text:
            Natural-language constraint description.

        Returns
        -------
        str
            BSL directive string such as ``"FORBID: expose PII"`` or
            ``"REQUIRE: validate input"``.
        """
        if not text or not text.strip():
            return f"{self._fallback_prefix}: "

        cleaned = text.strip()
        normalised = _strip_subject_prefix(cleaned)

        for translation_pattern in self._patterns:
            match = translation_pattern.pattern.match(normalised)
            if match is None:
                # Try matching the original (un-stripped) text too
                match = translation_pattern.pattern.match(cleaned)
            if match is not None:
                body = _clean_body(match.group(translation_pattern.body_group))
                return f"{translation_pattern.bsl_keyword}: {body}"

        # No pattern matched — use fallback
        body = _clean_body(normalised)
        return f"{self._fallback_prefix}: {body}"

    def add_pattern(self, pattern: TranslationPattern) -> None:
        """Prepend *pattern* to the pattern list (highest priority).

        Parameters
        ----------
        pattern:
            A :class:`TranslationPattern` to add at the front of the
            matching sequence.
        """
        self._patterns.insert(0, pattern)

    def list_patterns(self) -> list[TranslationPattern]:
        """Return a copy of the current pattern list.

        Returns
        -------
        list[TranslationPattern]
            All registered patterns in matching order.
        """
        return list(self._patterns)

    @property
    def pattern_count(self) -> int:
        """Return the number of registered patterns."""
        return len(self._patterns)


__all__ = [
    "TranslationPattern",
    "TemplateTranslator",
]
