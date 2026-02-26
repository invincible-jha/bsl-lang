"""BSL canonical formatter: AST → formatted BSL source text.

The ``BslFormatter`` takes an ``AgentSpec`` AST and renders it as
canonically formatted BSL text with:

- 2-space indentation
- Blank lines between top-level blocks (behaviors, invariants, etc.)
- Sorted metadata fields (version, model, owner always first in that order)
- Consistent spacing around operators
- COMMENT tokens are not preserved (the formatter works from the AST)

This formatter is used by ``bsl fmt`` to enforce a consistent code style
across a codebase.

Usage
-----
::

    from bsl.formatter import BslFormatter
    from bsl.parser import parse

    spec = parse(source)
    formatter = BslFormatter()
    canonical = formatter.format(spec)
"""
from __future__ import annotations

from bsl.ast.nodes import (
    AfterExpr,
    AgentSpec,
    AuditLevel,
    Behavior,
    BeforeExpr,
    BinOp,
    BinaryOpExpr,
    BoolLit,
    Composition,
    Constraint,
    ContainsExpr,
    Degradation,
    Delegates,
    DotAccess,
    EscalationClause,
    Expression,
    FunctionCall,
    Identifier,
    InListExpr,
    Invariant,
    NumberLit,
    Receives,
    ShouldConstraint,
    Span,
    StringLit,
    ThresholdClause,
    UnaryOpExpr,
)

_INDENT = "  "  # 2 spaces per level

_BINOP_SYMBOLS: dict[BinOp, str] = {
    BinOp.AND: "and",
    BinOp.OR: "or",
    BinOp.EQ: "==",
    BinOp.NEQ: "!=",
    BinOp.LT: "<",
    BinOp.GT: ">",
    BinOp.LTE: "<=",
    BinOp.GTE: ">=",
    BinOp.BEFORE: "before",
    BinOp.AFTER: "after",
    BinOp.CONTAINS: "contains",
    BinOp.IN: "in",
}


class BslFormatter:
    """Produces canonical BSL text from an ``AgentSpec`` AST.

    All output uses 2-space indentation and follows the canonical
    clause ordering defined in ``bsl.grammar.grammar``.
    """

    def format(self, spec: AgentSpec) -> str:
        """Render ``spec`` as a canonical BSL string.

        Parameters
        ----------
        spec:
            The agent specification to format.

        Returns
        -------
        str
            Canonical BSL source text, always ending with a newline.
        """
        lines: list[str] = []
        lines.append(f"agent {spec.name} {{")

        # Metadata (sorted canonical order)
        if spec.version is not None:
            lines.append(f"{_INDENT}version: {self._format_string(spec.version)}")
        if spec.model is not None:
            lines.append(f"{_INDENT}model: {self._format_string(spec.model)}")
        if spec.owner is not None:
            lines.append(f"{_INDENT}owner: {self._format_string(spec.owner)}")

        # Behaviors
        for behavior in spec.behaviors:
            lines.append("")
            lines.extend(self._format_behavior(behavior))

        # Invariants
        for invariant in spec.invariants:
            lines.append("")
            lines.extend(self._format_invariant(invariant))

        # Degradations
        for degradation in spec.degradations:
            lines.append("")
            lines.append(self._format_degradation(degradation))

        # Compositions
        for composition in spec.compositions:
            lines.append("")
            lines.append(self._format_composition(composition))

        lines.append("}")
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Behavior formatting
    # ------------------------------------------------------------------

    def _format_behavior(self, b: Behavior) -> list[str]:
        lines: list[str] = []
        indent = _INDENT
        lines.append(f"{indent}behavior {b.name} {{")
        inner = _INDENT * 2

        if b.when_clause is not None:
            lines.append(f"{inner}when: {self._format_expr(b.when_clause)}")
        if b.confidence is not None:
            lines.append(f"{inner}confidence: {self._format_threshold(b.confidence)}")
        if b.latency is not None:
            lines.append(f"{inner}latency: {self._format_threshold(b.latency)}")
        if b.cost is not None:
            lines.append(f"{inner}cost: {self._format_threshold(b.cost)}")
        if b.audit != AuditLevel.NONE:
            lines.append(f"{inner}audit: {b.audit.name.lower()}")
        if b.escalation is not None:
            lines.append(f"{inner}escalate_to_human when: {self._format_expr(b.escalation.condition)}")

        for c in b.must_constraints:
            lines.append(f"{inner}must: {self._format_expr(c.expression)}")
        for c in b.must_not_constraints:
            lines.append(f"{inner}must_not: {self._format_expr(c.expression)}")
        for c in b.should_constraints:
            lines.append(self._format_should(c, inner))
        for c in b.may_constraints:
            lines.append(f"{inner}may: {self._format_expr(c.expression)}")

        lines.append(f"{indent}}}")
        return lines

    def _format_should(self, c: ShouldConstraint, indent: str) -> str:
        base = f"{indent}should: {self._format_expr(c.expression)}"
        if c.percentage is not None:
            pct = int(c.percentage) if c.percentage == int(c.percentage) else c.percentage
            base += f" {pct}% of cases"
        return base

    def _format_threshold(self, t: ThresholdClause) -> str:
        pct = "%" if t.is_percentage else ""
        value = int(t.value) if t.value == int(t.value) else t.value
        return f"{t.operator}{value}{pct}"

    # ------------------------------------------------------------------
    # Invariant formatting
    # ------------------------------------------------------------------

    def _format_invariant(self, inv: Invariant) -> list[str]:
        from bsl.ast.nodes import AppliesTo

        lines: list[str] = []
        indent = _INDENT
        inner = _INDENT * 2
        lines.append(f"{indent}invariant {inv.name} {{")

        if inv.applies_to == AppliesTo.ALL_BEHAVIORS:
            lines.append(f"{inner}applies_to: all_behaviors")
        else:
            names = ", ".join(inv.named_behaviors)
            lines.append(f"{inner}applies_to: [{names}]")

        lines.append(f"{inner}severity: {inv.severity.name.lower()}")

        for c in inv.constraints:
            lines.append(f"{inner}must: {self._format_expr(c.expression)}")
        for c in inv.prohibitions:
            lines.append(f"{inner}must_not: {self._format_expr(c.expression)}")

        lines.append(f"{indent}}}")
        return lines

    # ------------------------------------------------------------------
    # Degradation and composition formatting
    # ------------------------------------------------------------------

    def _format_degradation(self, d: Degradation) -> str:
        indent = _INDENT
        return f"{indent}degrades_to {d.fallback} when: {self._format_expr(d.condition)}"

    def _format_composition(self, c: Composition) -> str:
        indent = _INDENT
        if isinstance(c, Receives):
            return f"{indent}receives from {c.source_agent}"
        if isinstance(c, Delegates):
            return f"{indent}delegates_to {c.target_agent}"
        return f"{indent}{c!r}"

    # ------------------------------------------------------------------
    # Expression formatting
    # ------------------------------------------------------------------

    def _format_expr(self, expr: Expression) -> str:
        """Render an expression node to a compact string."""
        if isinstance(expr, Identifier):
            return expr.name
        if isinstance(expr, DotAccess):
            return ".".join(expr.parts)
        if isinstance(expr, StringLit):
            return self._format_string(expr.value)
        if isinstance(expr, NumberLit):
            value = int(expr.value) if expr.value == int(expr.value) else expr.value
            return str(value)
        if isinstance(expr, BoolLit):
            return "true" if expr.value else "false"
        if isinstance(expr, BinaryOpExpr):
            left = self._format_expr(expr.left)
            right = self._format_expr(expr.right)
            op = _BINOP_SYMBOLS.get(expr.op, expr.op.name.lower())
            # Wrap in parens if nested boolean operators to ensure clarity
            if expr.op in (BinOp.AND, BinOp.OR):
                left_str = f"({left})" if isinstance(expr.left, BinaryOpExpr) and expr.left.op in (BinOp.AND, BinOp.OR) and expr.left.op != expr.op else left
                right_str = f"({right})" if isinstance(expr.right, BinaryOpExpr) and expr.right.op in (BinOp.AND, BinOp.OR) and expr.right.op != expr.op else right
                return f"{left_str} {op} {right_str}"
            return f"{left} {op} {right}"
        if isinstance(expr, UnaryOpExpr):
            return f"not {self._format_expr(expr.operand)}"
        if isinstance(expr, FunctionCall):
            args = ", ".join(self._format_expr(a) for a in expr.arguments)
            return f"{expr.name}({args})"
        if isinstance(expr, ContainsExpr):
            return f"{self._format_expr(expr.subject)} contains {self._format_expr(expr.value)}"
        if isinstance(expr, InListExpr):
            items = ", ".join(self._format_expr(i) for i in expr.items)
            return f"{self._format_expr(expr.subject)} in [{items}]"
        if isinstance(expr, BeforeExpr):
            return f"{self._format_expr(expr.left)} before {self._format_expr(expr.right)}"
        if isinstance(expr, AfterExpr):
            return f"{self._format_expr(expr.left)} after {self._format_expr(expr.right)}"
        return repr(expr)

    @staticmethod
    def _format_string(value: str) -> str:
        """Render a Python string as a BSL double-quoted string literal."""
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'


def format_spec(spec: AgentSpec) -> str:
    """Convenience function: format an ``AgentSpec`` to canonical BSL text.

    Parameters
    ----------
    spec:
        The agent specification to format.

    Returns
    -------
    str
        Canonical BSL source text.
    """
    return BslFormatter().format(spec)
