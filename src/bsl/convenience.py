"""Convenience API for bsl-lang — 3-line quickstart.

The top-level ``bsl`` module already exposes ``parse`` and ``validate``
as module-level functions. This module re-exports them and adds a
``BslSpec`` convenience wrapper for the common parse-then-validate flow.

Example
-------
::

    import bsl
    spec = bsl.parse("agent Demo { version: '1.0' owner: 'dev@example.com' }")
    issues = bsl.validate(spec)

"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from bsl.ast.nodes import AgentSpec
    from bsl.validator.diagnostics import Diagnostic


class BslSpec:
    """Zero-config BSL specification wrapper.

    Parses BSL source text and wraps the resulting AST with convenience
    methods for validate, format, and export.

    Parameters
    ----------
    source:
        BSL source text to parse. If empty, a minimal valid spec is used.

    Example
    -------
    ::

        from bsl import BslSpec
        spec = BslSpec("agent Demo { version: '1.0' owner: 'dev@example.com' }")
        issues = spec.validate()
        canonical = spec.format()
    """

    _MINIMAL_SOURCE = (
        "agent QuickstartAgent {\n"
        '  version: "1.0"\n'
        '  owner: "dev@example.com"\n'
        "}\n"
    )

    def __init__(self, source: str = "") -> None:
        import bsl as _bsl

        effective_source = source if source.strip() else self._MINIMAL_SOURCE
        self._ast: AgentSpec = _bsl.parse(effective_source)
        self._source = effective_source

    @property
    def ast(self) -> "AgentSpec":
        """The parsed AgentSpec AST."""
        return self._ast

    def validate(self, strict: bool = False) -> list["Diagnostic"]:
        """Validate the specification.

        Parameters
        ----------
        strict:
            When True, warnings are promoted to errors.

        Returns
        -------
        list[Diagnostic]
            All validation findings.
        """
        import bsl as _bsl
        return _bsl.validate(self._ast, strict=strict)

    def format(self) -> str:
        """Return the spec formatted to canonical BSL style.

        Returns
        -------
        str
            Canonical BSL source text.
        """
        import bsl as _bsl
        return _bsl.format(self._ast)

    def export_schema(self) -> dict[str, Any]:
        """Export the spec as a JSON Schema dict.

        Returns
        -------
        dict[str, Any]
            JSON Schema (draft 2020-12) document.
        """
        import bsl as _bsl
        return _bsl.export_schema(self._ast)

    def is_valid(self) -> bool:
        """Return True if the spec has no ERROR-level diagnostics.

        Returns
        -------
        bool
        """
        diagnostics = self.validate()
        return all(d.severity.value != "error" for d in diagnostics)

    def __repr__(self) -> str:
        agent_name = getattr(self._ast, "name", "unknown")
        return f"BslSpec(agent={agent_name!r})"
