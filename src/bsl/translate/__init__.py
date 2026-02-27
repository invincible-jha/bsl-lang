"""BSL Natural Language Translation module.

Provides tools for translating between natural-language constraint
descriptions and BSL (Behavioral Specification Language) directives.

Two translation directions are supported:

- **NL → BSL** via :class:`~bsl.translate.nl_to_bsl.NLToBSLTranslator`
- **BSL → NL** via :class:`~bsl.translate.bsl_to_nl.BSLToNLTranslator`

Three provider implementations are included:

- :class:`~bsl.translate.providers.TemplateProvider` — rule-based,
  **no LLM required**, suitable for offline/CI use.
- :class:`~bsl.translate.providers.MockLLMProvider` — deterministic
  stub, used in all automated tests; never calls external APIs.
- :class:`~bsl.translate.providers.TranslationProvider` — Protocol
  that third-party LLM back-ends must satisfy.

Quick start
-----------
::

    from bsl.translate import NLToBSLTranslator, BSLToNLTranslator, TemplateProvider

    translator = NLToBSLTranslator(provider=TemplateProvider())

    bsl = translator.translate("must never expose user credentials")
    # 'FORBID: expose user credentials'

    nl_translator = BSLToNLTranslator(provider=TemplateProvider())
    # TemplateProvider used as pass-through for NL in BSL→NL direction;
    # for richer output use MockLLMProvider or a real LLM provider.
"""
from __future__ import annotations

from bsl.translate.bsl_to_nl import BSLToNLTranslator
from bsl.translate.nl_to_bsl import NLToBSLTranslator, TranslationError
from bsl.translate.providers import MockLLMProvider, TemplateProvider, TranslationProvider
from bsl.translate.templates import TemplateTranslator, TranslationPattern

__all__ = [
    "NLToBSLTranslator",
    "BSLToNLTranslator",
    "TranslationError",
    "TranslationProvider",
    "MockLLMProvider",
    "TemplateProvider",
    "TemplateTranslator",
    "TranslationPattern",
]
