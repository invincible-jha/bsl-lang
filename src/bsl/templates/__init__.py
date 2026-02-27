"""BSL Template Library package.

Provides a registry of 20+ domain-specific BSL templates that can be
loaded, listed, and used as starting points for new agent specifications.
"""
from __future__ import annotations

from bsl.templates.library import TemplateLibrary, TemplateMetadata

__all__ = [
    "TemplateLibrary",
    "TemplateMetadata",
]
