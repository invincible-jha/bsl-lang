"""BSL → NL translator.

Converts BSL directives back into readable natural-language descriptions.

Usage
-----
::

    from bsl.translate.providers import MockLLMProvider, TemplateProvider
    from bsl.translate.bsl_to_nl import BSLToNLTranslator

    # With the mock provider (deterministic, used in tests)
    translator = BSLToNLTranslator(provider=MockLLMProvider())
    result = translator.translate("FORBID: expose credentials")
    # 'The agent must never expose credentials.'

    # With a template provider (no LLM required)
    translator = BSLToNLTranslator(provider=TemplateProvider())
"""
from __future__ import annotations

import re
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bsl.translate.providers import TranslationProvider

from typing import Callable

from bsl.translate.nl_to_bsl import TranslationError

# ---------------------------------------------------------------------------
# Built-in BSL → NL rule table
# ---------------------------------------------------------------------------

# Maps a BSL keyword (upper-case) to a callable that takes the body string
# and returns a human-readable English sentence.
_BSL_KEYWORD_TO_NL: dict[str, Callable[[str], str]] = {
    "FORBID": lambda body: f"The agent must never {body}.",
    "REQUIRE": lambda body: f"The agent must always {body}.",
    "RECOMMEND": lambda body: f"The agent should {body}.",
    "LIMIT": lambda body: f"The agent must not exceed {body}.",
    "DENY": lambda body: f"The agent is denied access to {body}.",
    "ALLOW": lambda body: f"The agent is permitted to {body}.",
    "WARN": lambda body: f"The agent must warn when {body}.",
    "AUDIT": lambda body: f"The agent must audit {body}.",
    "LOG": lambda body: f"The agent must log {body}.",
    "ENFORCE": lambda body: f"The agent must enforce {body}.",
    "RATE_LIMIT": lambda body: f"The agent must apply rate limiting of {body}.",
    "TIMEOUT": lambda body: f"The agent must time out after {body}.",
    "RETRY": lambda body: f"The agent must retry up to {body}.",
}

# Pattern that recognises a BSL directive line: "KEYWORD: body"
_BSL_DIRECTIVE_RE = re.compile(
    r"^([A-Z][A-Z0-9_]*):\s*(.*)$",
    re.MULTILINE,
)


def _translate_directive_builtin(keyword: str, body: str) -> str | None:
    """Attempt to translate a single BSL directive using the built-in table.

    Parameters
    ----------
    keyword:
        Upper-case BSL keyword (e.g. ``"FORBID"``).
    body:
        The body of the directive (everything after ``": "``).

    Returns
    -------
    str | None
        Natural-language sentence, or ``None`` if the keyword is not
        in the built-in table.
    """
    factory = _BSL_KEYWORD_TO_NL.get(keyword.upper())
    if factory is None:
        return None
    return factory(body.strip())


class BSLToNLTranslator:
    """Translates BSL directives into natural-language descriptions.

    For single-directive inputs the translator first attempts a lookup in
    the built-in keyword table.  If the provider is supplied, it is used
    instead (or as a fallback for unknown keywords).

    Parameters
    ----------
    provider:
        A :class:`~bsl.translate.providers.TranslationProvider` used
        for translation.  When ``None``, the built-in keyword table is
        used and a :class:`RuntimeWarning` is emitted for inputs that
        contain unknown keywords.

    Examples
    --------
    ::

        from bsl.translate.bsl_to_nl import BSLToNLTranslator
        from bsl.translate.providers import MockLLMProvider

        translator = BSLToNLTranslator(provider=MockLLMProvider())
        translator.translate("REQUIRE: validate input schema")
        # 'The agent must always validate input schema.'
    """

    def __init__(self, provider: "TranslationProvider | None" = None) -> None:
        if provider is None:
            warnings.warn(
                "No TranslationProvider supplied to BSLToNLTranslator; "
                "built-in keyword table will be used. "
                "Unknown BSL keywords will produce a generic fallback. "
                "Pass an explicit provider to suppress this warning.",
                RuntimeWarning,
                stacklevel=2,
            )
        self._provider: "TranslationProvider | None" = provider

    def translate(self, bsl_text: str) -> str:
        """Translate a BSL directive string into natural language.

        Parameters
        ----------
        bsl_text:
            A BSL directive such as ``"FORBID: share credentials"`` or
            a multi-line block of BSL directives.

        Returns
        -------
        str
            Human-readable natural-language description.

        Raises
        ------
        TranslationError
            If the provider raises an unexpected exception.
        ValueError
            If *bsl_text* is ``None``.
        """
        if bsl_text is None:  # type: ignore[comparison-overlap]
            raise ValueError("translate() requires a str, got None")

        normalised = bsl_text.strip()

        # If a provider was supplied, delegate entirely to it.
        if self._provider is not None:
            try:
                result: str = self._provider.translate(normalised)
            except TranslationError:
                raise
            except Exception as exc:
                raise TranslationError(
                    f"Translation provider failed: {exc}",
                    original_text=bsl_text,
                ) from exc
            return result

        # Built-in path: try single-directive match first.
        match = _BSL_DIRECTIVE_RE.match(normalised)
        if match:
            keyword, body = match.group(1), match.group(2)
            nl_sentence = _translate_directive_builtin(keyword, body)
            if nl_sentence is not None:
                return nl_sentence
            # Unknown keyword — produce a readable generic sentence.
            return f"The agent is subject to the following constraint: {normalised}."

        # Multi-line or unstructured input — translate line by line.
        lines = [line.strip() for line in normalised.splitlines() if line.strip()]
        parts: list[str] = []
        for line in lines:
            m = _BSL_DIRECTIVE_RE.match(line)
            if m:
                keyword, body = m.group(1), m.group(2)
                sentence = _translate_directive_builtin(keyword, body)
                parts.append(sentence if sentence is not None else f"Constraint: {line}.")
            else:
                parts.append(line)
        return " ".join(parts)

    def translate_batch(self, bsl_texts: list[str]) -> list[str]:
        """Translate a sequence of BSL directives to natural language.

        Parameters
        ----------
        bsl_texts:
            List of BSL directive strings.

        Returns
        -------
        list[str]
            Natural-language strings in the same order as *bsl_texts*.

        Raises
        ------
        TranslationError
            If any single translation fails.
        """
        return [self.translate(text) for text in bsl_texts]

    @property
    def provider(self) -> "TranslationProvider | None":
        """Return the current translation provider (may be ``None``)."""
        return self._provider


__all__ = [
    "BSLToNLTranslator",
]
