"""NL → BSL translator.

Converts natural-language constraint descriptions into BSL directives.

Usage
-----
::

    from bsl.translate.providers import MockLLMProvider, TemplateProvider
    from bsl.translate.nl_to_bsl import NLToBSLTranslator

    # With a template (no LLM required)
    translator = NLToBSLTranslator(provider=TemplateProvider())
    result = translator.translate("must never expose credentials")
    # 'FORBID: expose credentials'

    # With the mock provider (deterministic, used in tests)
    translator = NLToBSLTranslator(provider=MockLLMProvider())
    result = translator.translate("must always validate input")
    # 'REQUIRE: validate input'
"""
from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bsl.translate.providers import TranslationProvider


class TranslationError(Exception):
    """Raised when a translation attempt fails irrecoverably.

    Parameters
    ----------
    message:
        Human-readable error description.
    original_text:
        The input text that could not be translated.
    """

    def __init__(self, message: str, original_text: str = "") -> None:
        super().__init__(message)
        self.original_text = original_text


class NLToBSLTranslator:
    """Translates natural-language text into BSL directives.

    Parameters
    ----------
    provider:
        A :class:`~bsl.translate.providers.TranslationProvider` that
        performs the actual translation.  When ``None``, the module
        falls back to :class:`~bsl.translate.providers.TemplateProvider`
        and emits a :class:`RuntimeWarning`.

    Examples
    --------
    ::

        from bsl.translate.providers import TemplateProvider
        from bsl.translate.nl_to_bsl import NLToBSLTranslator

        translator = NLToBSLTranslator(provider=TemplateProvider())
        translator.translate("must never share credentials")
        # 'FORBID: share credentials'
    """

    def __init__(self, provider: "TranslationProvider | None" = None) -> None:
        if provider is None:
            warnings.warn(
                "No TranslationProvider supplied to NLToBSLTranslator; "
                "falling back to TemplateProvider. "
                "Pass an explicit provider to suppress this warning.",
                RuntimeWarning,
                stacklevel=2,
            )
            from bsl.translate.providers import TemplateProvider

            provider = TemplateProvider()
        self._provider: "TranslationProvider" = provider

    def translate(self, text: str) -> str:
        """Translate *text* from natural language to a BSL directive.

        Parameters
        ----------
        text:
            Natural-language constraint description such as
            ``"must never expose user PII"``.

        Returns
        -------
        str
            A BSL directive string, e.g. ``"FORBID: expose user PII"``.

        Raises
        ------
        TranslationError
            If the provider raises an unexpected exception.
        ValueError
            If *text* is ``None``.
        """
        if text is None:  # type: ignore[comparison-overlap]
            raise ValueError("translate() requires a str, got None")

        normalised = text.strip()
        try:
            result: str = self._provider.translate(normalised)
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError(
                f"Translation provider failed: {exc}",
                original_text=text,
            ) from exc

        return result

    def translate_batch(self, texts: list[str]) -> list[str]:
        """Translate a sequence of natural-language descriptions.

        Parameters
        ----------
        texts:
            List of natural-language strings to translate.

        Returns
        -------
        list[str]
            BSL directive strings in the same order as *texts*.

        Raises
        ------
        TranslationError
            If any single translation fails.
        """
        return [self.translate(text) for text in texts]

    @property
    def provider(self) -> "TranslationProvider":
        """Return the current translation provider."""
        return self._provider


__all__ = [
    "NLToBSLTranslator",
    "TranslationError",
]
