"""BSL Validator: semantic analysis of a parsed ``AgentSpec``.

The ``Validator`` runs a configurable set of validation rules against
an ``AgentSpec`` and returns a list of ``Diagnostic`` objects.  In
strict mode, warnings are promoted to errors so that CI pipelines can
enforce tighter quality gates.

Usage
-----
::

    from bsl.parser import parse
    from bsl.validator import Validator

    spec = parse(source)
    validator = Validator()
    diagnostics = validator.validate(spec)
    errors = [d for d in diagnostics if d.is_error]
"""
from __future__ import annotations

from bsl.ast.nodes import AgentSpec
from bsl.validator.diagnostics import Diagnostic, DiagnosticSeverity
from bsl.validator.rules import DEFAULT_RULES, Rule


class Validator:
    """Semantic validator for BSL agent specifications.

    Parameters
    ----------
    rules:
        The list of validation rules to run.  Defaults to all built-in
        rules (``DEFAULT_RULES``).  Pass a custom list to extend or
        restrict which rules apply.
    strict:
        When ``True``, WARNING-level diagnostics are promoted to ERROR
        severity, causing the overall validation to fail on warnings.
    """

    def __init__(
        self,
        rules: list[Rule] | None = None,
        strict: bool = False,
    ) -> None:
        self._rules: list[Rule] = rules if rules is not None else list(DEFAULT_RULES)
        self._strict: bool = strict

    def validate(self, spec: AgentSpec) -> list[Diagnostic]:
        """Run all rules against ``spec`` and return the collected diagnostics.

        Parameters
        ----------
        spec:
            The ``AgentSpec`` AST node to validate.

        Returns
        -------
        list[Diagnostic]
            All findings, sorted by source line then column.  May be
            empty if the spec is valid.
        """
        all_diagnostics: list[Diagnostic] = []
        for rule in self._rules:
            try:
                all_diagnostics.extend(rule(spec))
            except Exception as exc:  # noqa: BLE001
                # Rule implementation errors should not crash the validator;
                # record them as internal errors instead.
                from bsl.ast.nodes import Span

                all_diagnostics.append(
                    Diagnostic(
                        severity=DiagnosticSeverity.ERROR,
                        code="BSL999",
                        message=f"Internal validator error in rule {rule.__name__!r}: {exc}",
                        span=spec.span,
                        suggestion="Please report this as a bug",
                        rule=rule.__name__,
                    )
                )

        if self._strict:
            all_diagnostics = [
                Diagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    code=d.code,
                    message=d.message,
                    span=d.span,
                    suggestion=d.suggestion,
                    rule=d.rule,
                )
                if d.severity == DiagnosticSeverity.WARNING
                else d
                for d in all_diagnostics
            ]

        # Sort by line, then column for deterministic output
        all_diagnostics.sort(key=lambda d: (d.span.line, d.span.col))
        return all_diagnostics

    def add_rule(self, rule: Rule) -> None:
        """Add a custom rule to this validator instance.

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


def validate(spec: AgentSpec, strict: bool = False) -> list[Diagnostic]:
    """Convenience function: validate an ``AgentSpec`` with default rules.

    Parameters
    ----------
    spec:
        The ``AgentSpec`` to validate.
    strict:
        If ``True``, warnings become errors.

    Returns
    -------
    list[Diagnostic]
        Sorted list of all findings.
    """
    return Validator(strict=strict).validate(spec)
