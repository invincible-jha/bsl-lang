"""bsl-lang — Behavioral Specification Language toolkit: parser, validator, formatter, linter.

Public API
----------
The stable public surface is everything exported from this module.
Anything inside submodules not re-exported here is considered private
and may change without notice.

Example
-------
::

    import bsl

    # Parse a BSL source string into an AST
    spec = bsl.parse('''
        agent GreetingAgent {
          version: "1.0"
          model: "gpt-4o"
          owner: "ai-team@example.com"
          behavior greet {
            must: response contains "Hello"
            confidence: >= 90%
            audit: basic
          }
        }
    ''')

    # Validate for correctness
    diagnostics = bsl.validate(spec)

    # Format to canonical style
    canonical = bsl.format(spec)

    # Export JSON Schema
    schema = bsl.export_schema(spec)

    # Diff two specs
    changes = bsl.diff(old_spec, spec)

    # Lint for quality issues
    findings = bsl.lint(spec)

    bsl.__version__
    '0.1.0'
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__: str = "0.1.0"

if TYPE_CHECKING:
    from bsl.ast.nodes import AgentSpec
    from bsl.diff.diff import BslChange
    from bsl.validator.diagnostics import Diagnostic


def parse(source: str) -> "AgentSpec":
    """Parse a BSL source string into an ``AgentSpec`` AST.

    Parameters
    ----------
    source:
        Complete BSL source text.

    Returns
    -------
    AgentSpec
        The parsed agent specification.

    Raises
    ------
    bsl.lexer.LexError
        If the source contains invalid characters.
    bsl.parser.ParseErrorCollection
        If the source contains syntactic errors.
    """
    from bsl.parser.parser import parse as _parse

    return _parse(source)


def validate(
    spec: "AgentSpec", strict: bool = False
) -> list["Diagnostic"]:
    """Validate an ``AgentSpec`` against all built-in rules.

    Parameters
    ----------
    spec:
        The agent specification to validate.
    strict:
        When ``True``, warnings are promoted to errors.

    Returns
    -------
    list[Diagnostic]
        All validation findings, sorted by source location.
    """
    from bsl.validator.validator import validate as _validate

    return _validate(spec, strict=strict)


def format(spec: "AgentSpec") -> str:  # noqa: A001
    """Format an ``AgentSpec`` to canonical BSL text.

    Parameters
    ----------
    spec:
        The agent specification to format.

    Returns
    -------
    str
        Canonical BSL source text ending with a newline.
    """
    from bsl.formatter.formatter import format_spec

    return format_spec(spec)


def diff(old: "AgentSpec", new: "AgentSpec") -> list["BslChange"]:
    """Compute structural changes between two ``AgentSpec`` objects.

    Parameters
    ----------
    old:
        The baseline specification.
    new:
        The updated specification.

    Returns
    -------
    list[BslChange]
        All structural changes from ``old`` to ``new``.
    """
    from bsl.diff.diff import diff as _diff

    return _diff(old, new)


def lint(spec: "AgentSpec", include_hints: bool = True) -> list["Diagnostic"]:
    """Lint an ``AgentSpec`` for style and quality issues.

    Parameters
    ----------
    spec:
        The agent specification to lint.
    include_hints:
        If ``False``, HINT-level findings are suppressed.

    Returns
    -------
    list[Diagnostic]
        All lint findings, sorted by source location.
    """
    from bsl.linter.linter import lint as _lint

    return _lint(spec, include_hints=include_hints)


def export_schema(spec: "AgentSpec") -> dict[str, Any]:
    """Export an ``AgentSpec`` as a JSON Schema dict.

    Parameters
    ----------
    spec:
        The agent specification to export.

    Returns
    -------
    dict[str, Any]
        A JSON Schema (draft 2020-12) document.
    """
    from bsl.schema.json_schema import export_schema as _export_schema

    return _export_schema(spec)


__all__ = [
    "__version__",
    "parse",
    "validate",
    "format",
    "diff",
    "lint",
    "export_schema",
]
