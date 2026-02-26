"""BSL Linter: style and quality checks for BSL agent specifications.

The ``BslLinter`` runs a configurable set of lint rules against an
``AgentSpec`` and returns ``Diagnostic`` objects.  Unlike the
``Validator`` (which checks correctness), the linter checks quality,
style, and completeness — findings are typically WARNING or HINT level.

Usage
-----
::

    from bsl.parser import parse
    from bsl.linter import BslLinter

    spec = parse(source)
    linter = BslLinter()
    diagnostics = linter.lint(spec)
"""
from __future__ import annotations

from bsl.ast.nodes import AgentSpec
from bsl.linter.rules import ALL_LINT_RULES
from bsl.validator.diagnostics import Diagnostic, DiagnosticSeverity
from bsl.validator.rules import Rule


class BslLinter:
    """Configurable BSL linter.

    Parameters
    ----------
    rules:
        Lint rules to run.  Defaults to all built-in rules
        (naming, completeness, and consistency).
    include_hints:
        If ``False``, HINT-level diagnostics are suppressed.
    """

    def __init__(
        self,
        rules: list[Rule] | None = None,
        include_hints: bool = True,
    ) -> None:
        self._rules: list[Rule] = rules if rules is not None else list(ALL_LINT_RULES)
        self._include_hints = include_hints

    def lint(self, spec: AgentSpec) -> list[Diagnostic]:
        """Run all lint rules against ``spec``.

        Parameters
        ----------
        spec:
            The ``AgentSpec`` to lint.

        Returns
        -------
        list[Diagnostic]
            All lint findings, sorted by source line then column.
        """
        all_diagnostics: list[Diagnostic] = []
        for rule in self._rules:
            try:
                all_diagnostics.extend(rule(spec))
            except Exception as exc:  # noqa: BLE001
                from bsl.ast.nodes import Span

                all_diagnostics.append(
                    Diagnostic(
                        severity=DiagnosticSeverity.ERROR,
                        code="LINT-999",
                        message=f"Internal linter error in rule {rule.__name__!r}: {exc}",
                        span=spec.span,
                        suggestion="Please report this as a bug",
                        rule=rule.__name__,
                    )
                )

        if not self._include_hints:
            all_diagnostics = [
                d for d in all_diagnostics if d.severity != DiagnosticSeverity.HINT
            ]

        all_diagnostics.sort(key=lambda d: (d.span.line, d.span.col))
        return all_diagnostics

    def add_rule(self, rule: Rule) -> None:
        """Add a custom lint rule.

        Parameters
        ----------
        rule:
            A callable ``(AgentSpec) -> list[Diagnostic]``.
        """
        self._rules.append(rule)

    @property
    def rule_count(self) -> int:
        """Return the number of rules currently registered."""
        return len(self._rules)


def lint(spec: AgentSpec, include_hints: bool = True) -> list[Diagnostic]:
    """Convenience function: lint an ``AgentSpec`` with all default rules.

    Parameters
    ----------
    spec:
        The ``AgentSpec`` to lint.
    include_hints:
        If ``False``, HINT-level diagnostics are suppressed.

    Returns
    -------
    list[Diagnostic]
        Sorted list of all lint findings.
    """
    return BslLinter(include_hints=include_hints).lint(spec)
