"""TemplateLibrary — registry of domain-specific BSL templates.

Provides :class:`TemplateLibrary` for loading, listing, and retrieving
BSL template strings by name.  Built-in templates cover 20+ domains
and are sourced from :mod:`bsl.templates.builtin_templates`.

Usage
-----
::

    from bsl.templates import TemplateLibrary

    lib = TemplateLibrary()
    print(lib.list_templates())
    bsl_source = lib.load_template("healthcare")

    # Register a custom template
    lib.register("my_domain", source="agent MyBot { ... }", domain="custom")
    assert "my_domain" in lib.list_names()
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TemplateMetadata:
    """Metadata for a single BSL template entry.

    Parameters
    ----------
    name:
        Unique registry key for this template.
    domain:
        High-level category, e.g. ``"healthcare"``, ``"finance"``.
    description:
        One-sentence summary of the agent's purpose.
    tags:
        Free-form labels for search/filtering.
    version:
        Semantic version string for the template itself.
    """

    name: str
    domain: str
    description: str
    tags: tuple[str, ...] = ()
    version: str = "1.0"


# ---------------------------------------------------------------------------
# Internal registry entry
# ---------------------------------------------------------------------------


@dataclass
class _TemplateEntry:
    metadata: TemplateMetadata
    source: str


# ---------------------------------------------------------------------------
# TemplateLibrary
# ---------------------------------------------------------------------------


class TemplateLibrary:
    """Registry of BSL templates indexed by name.

    Built-in templates from :mod:`bsl.templates.builtin_templates` are
    loaded on first use (lazy initialization).  Additional templates can
    be registered at runtime via :meth:`register`.

    Parameters
    ----------
    auto_load_builtins:
        If ``True`` (default), the 20+ built-in templates are registered
        automatically at construction time.

    Raises
    ------
    KeyError
        When :meth:`load_template` is called with an unknown name.
    ValueError
        When :meth:`register` is called with a duplicate name and
        ``overwrite=False``.
    """

    def __init__(self, auto_load_builtins: bool = True) -> None:
        self._registry: dict[str, _TemplateEntry] = {}
        if auto_load_builtins:
            self._load_builtins()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_builtins(self) -> None:
        """Import and register all built-in templates."""
        from bsl.templates.builtin_templates import BUILTIN_TEMPLATES

        for name, (meta, source) in BUILTIN_TEMPLATES.items():
            self._registry[name] = _TemplateEntry(metadata=meta, source=source)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        source: str,
        domain: str = "custom",
        description: str = "",
        tags: tuple[str, ...] = (),
        version: str = "1.0",
        overwrite: bool = False,
    ) -> None:
        """Register a new template under *name*.

        Parameters
        ----------
        name:
            Registry key.  Must be unique unless *overwrite* is True.
        source:
            Raw BSL source string for the template.
        domain:
            Domain category (default ``"custom"``).
        description:
            Human-readable description.
        tags:
            Tuple of string tags for filtering.
        version:
            Template version string (default ``"1.0"``).
        overwrite:
            If ``True``, an existing entry with the same name is replaced.

        Raises
        ------
        ValueError
            If *name* is already registered and *overwrite* is False.
        """
        if name in self._registry and not overwrite:
            raise ValueError(
                f"Template '{name}' is already registered. "
                "Use overwrite=True to replace it."
            )
        meta = TemplateMetadata(
            name=name,
            domain=domain,
            description=description,
            tags=tags,
            version=version,
        )
        self._registry[name] = _TemplateEntry(metadata=meta, source=source)

    def load_template(self, name: str) -> str:
        """Return the BSL source string for template *name*.

        Parameters
        ----------
        name:
            The registry key of the template to load.

        Returns
        -------
        str
            The raw BSL source for the named template.

        Raises
        ------
        KeyError
            If no template with the given *name* is registered.
        """
        try:
            return self._registry[name].source
        except KeyError:
            available = sorted(self._registry.keys())
            raise KeyError(
                f"Template '{name}' not found. "
                f"Available templates: {available}"
            ) from None

    def get_metadata(self, name: str) -> TemplateMetadata:
        """Return metadata for template *name*.

        Parameters
        ----------
        name:
            The registry key.

        Returns
        -------
        TemplateMetadata

        Raises
        ------
        KeyError
            If no template with the given *name* is registered.
        """
        try:
            return self._registry[name].metadata
        except KeyError:
            raise KeyError(f"Template '{name}' not found.") from None

    def list_templates(self) -> list[TemplateMetadata]:
        """Return metadata for all registered templates, sorted by name.

        Returns
        -------
        list[TemplateMetadata]
            All registered template metadata objects in alphabetical order.
        """
        return [
            entry.metadata
            for entry in sorted(self._registry.values(), key=lambda e: e.metadata.name)
        ]

    def list_names(self) -> list[str]:
        """Return all registered template names in sorted order."""
        return sorted(self._registry.keys())

    def list_by_domain(self, domain: str) -> list[TemplateMetadata]:
        """Return templates whose domain matches *domain* (case-insensitive).

        Parameters
        ----------
        domain:
            Domain string to filter by.

        Returns
        -------
        list[TemplateMetadata]
            Matching templates in alphabetical order.
        """
        domain_lower = domain.lower()
        return [
            entry.metadata
            for entry in sorted(self._registry.values(), key=lambda e: e.metadata.name)
            if entry.metadata.domain.lower() == domain_lower
        ]

    def search_by_tag(self, tag: str) -> list[TemplateMetadata]:
        """Return templates that include *tag* in their tag set (case-insensitive).

        Parameters
        ----------
        tag:
            Tag string to search for.

        Returns
        -------
        list[TemplateMetadata]
            Matching templates in alphabetical order.
        """
        tag_lower = tag.lower()
        return [
            entry.metadata
            for entry in sorted(self._registry.values(), key=lambda e: e.metadata.name)
            if any(t.lower() == tag_lower for t in entry.metadata.tags)
        ]

    def __len__(self) -> int:
        """Return the number of registered templates."""
        return len(self._registry)

    def __contains__(self, name: object) -> bool:
        """Return True if *name* is a registered template key."""
        return name in self._registry
