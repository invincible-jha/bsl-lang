"""AST expression → Python assertion code generator.

This module maps every BSL ``Expression`` variant to a Python expression
string suitable for use inside a ``assert`` statement.

The generated strings are plain Python — no external dependencies are
introduced by the generated code beyond the standard library.

Expression mapping reference
-----------------------------

BSL expression                      Python assertion
----------------------------------  ------------------------------------------
``response contains "Hello"``       ``"Hello" in response``
``status in [200, 201]``            ``status in (200, 201)``
``len(items) > 0``                  ``len(items) > 0``
``response.tone == "warm"``         ``response.tone == "warm"``
``not flagged``                     ``not flagged``
``a and b``                         ``a and b``
``a or b``                          ``a or b``
``x before y``                      ``_bsl_before(x, y)``  (helper injected)
``x after y``                       ``_bsl_after(x, y)``   (helper injected)
``true`` / ``false``                ``True`` / ``False``
"""
from __future__ import annotations

from bsl.ast.nodes import (
    AfterExpr,
    BeforeExpr,
    BinOp,
    BinaryOpExpr,
    BoolLit,
    ContainsExpr,
    DotAccess,
    Expression,
    FunctionCall,
    Identifier,
    InListExpr,
    NumberLit,
    StringLit,
    UnaryOpExpr,
    UnaryOpKind,
)

# Mapping from BinOp members to Python infix operators.
_BINOP_TO_PYTHON: dict[BinOp, str] = {
    BinOp.AND: "and",
    BinOp.OR: "or",
    BinOp.EQ: "==",
    BinOp.NEQ: "!=",
    BinOp.LT: "<",
    BinOp.GT: ">",
    BinOp.LTE: "<=",
    BinOp.GTE: ">=",
}

# BinOp members that require a temporal helper instead of an operator.
_TEMPORAL_BINOPS = frozenset({BinOp.BEFORE, BinOp.AFTER, BinOp.CONTAINS, BinOp.IN})

# Set of helper functions that may be emitted into generated files.
TEMPORAL_HELPERS = '''\
def _bsl_before(left: object, right: object) -> bool:
    """Return True if ``left`` occurs before ``right`` (sequence/index comparison)."""
    try:
        return bool(left) < bool(right)  # placeholder — override in fixture
    except TypeError:
        return False


def _bsl_after(left: object, right: object) -> bool:
    """Return True if ``left`` occurs after ``right`` (sequence/index comparison)."""
    try:
        return bool(left) > bool(right)  # placeholder — override in fixture
    except TypeError:
        return False
'''


class CodeGenerator:
    """Translate a BSL ``Expression`` tree into a Python expression string.

    Usage
    -----
    ::

        gen = CodeGenerator()
        python_expr = gen.generate(bsl_expression)
        # python_expr is a string like "response.tone == \"warm\""

    The generator is stateless — the same instance can be reused for
    multiple expression trees.
    """

    def generate(self, expression: Expression) -> str:
        """Translate *expression* to a Python expression string.

        Parameters
        ----------
        expression:
            Any node from the ``Expression`` union defined in
            ``bsl.ast.nodes``.

        Returns
        -------
        str
            A syntactically valid Python expression (no trailing newline).
        """
        return self._dispatch(expression)

    def generate_assertion(self, expression: Expression) -> str:
        """Return a complete ``assert`` statement for *expression*.

        Parameters
        ----------
        expression:
            The BSL expression to assert.

        Returns
        -------
        str
            E.g. ``'assert response.tone == "warm"'``
        """
        python_expr = self._dispatch(expression)
        return f"assert {python_expr}"

    def generate_negated_assertion(self, expression: Expression) -> str:
        """Return an ``assert not`` statement for *expression*.

        Used for ``must_not`` / ``prohibitions`` constraints.

        Parameters
        ----------
        expression:
            The BSL expression that must NOT hold.

        Returns
        -------
        str
            E.g. ``'assert not (response contains profanity)'``
        """
        python_expr = self._dispatch(expression)
        return f"assert not ({python_expr})"

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, node: Expression) -> str:
        """Dispatch to the correct private method for *node*'s type."""
        if isinstance(node, BinaryOpExpr):
            return self._binary_op(node)
        if isinstance(node, UnaryOpExpr):
            return self._unary_op(node)
        if isinstance(node, ContainsExpr):
            return self._contains(node)
        if isinstance(node, InListExpr):
            return self._in_list(node)
        if isinstance(node, BeforeExpr):
            return self._before(node)
        if isinstance(node, AfterExpr):
            return self._after(node)
        if isinstance(node, FunctionCall):
            return self._function_call(node)
        if isinstance(node, DotAccess):
            return self._dot_access(node)
        if isinstance(node, Identifier):
            return self._identifier(node)
        if isinstance(node, StringLit):
            return self._string_lit(node)
        if isinstance(node, NumberLit):
            return self._number_lit(node)
        if isinstance(node, BoolLit):
            return self._bool_lit(node)
        # Should never reach here for a well-formed AST.
        return repr(node)

    def _binary_op(self, node: BinaryOpExpr) -> str:
        left = self._dispatch(node.left)
        right = self._dispatch(node.right)
        if node.op in _BINOP_TO_PYTHON:
            operator = _BINOP_TO_PYTHON[node.op]
            # Wrap sub-expressions in parens when they contain lower-precedence ops.
            left = self._maybe_paren(node.left, left)
            right = self._maybe_paren(node.right, right)
            return f"{left} {operator} {right}"
        # Fallback for unmapped ops (should not occur in well-formed AST).
        return f"({left} {node.op.name.lower()} {right})"

    def _unary_op(self, node: UnaryOpExpr) -> str:
        operand = self._dispatch(node.operand)
        if node.op == UnaryOpKind.NOT:
            # Wrap compound expressions in parens.
            if isinstance(node.operand, BinaryOpExpr | ContainsExpr | InListExpr):
                return f"not ({operand})"
            return f"not {operand}"
        return f"({node.op.name.lower()} {operand})"

    def _contains(self, node: ContainsExpr) -> str:
        subject = self._dispatch(node.subject)
        value = self._dispatch(node.value)
        # BSL "response contains 'Hello'" → Python "Hello" in response
        # (``in`` membership check).
        return f"{value} in {subject}"

    def _in_list(self, node: InListExpr) -> str:
        subject = self._dispatch(node.subject)
        items = ", ".join(self._dispatch(item) for item in node.items)
        return f"{subject} in ({items},)"

    def _before(self, node: BeforeExpr) -> str:
        left = self._dispatch(node.left)
        right = self._dispatch(node.right)
        return f"_bsl_before({left}, {right})"

    def _after(self, node: AfterExpr) -> str:
        left = self._dispatch(node.left)
        right = self._dispatch(node.right)
        return f"_bsl_after({left}, {right})"

    def _function_call(self, node: FunctionCall) -> str:
        args = ", ".join(self._dispatch(arg) for arg in node.arguments)
        return f"{node.name}({args})"

    def _dot_access(self, node: DotAccess) -> str:
        return ".".join(node.parts)

    def _identifier(self, node: Identifier) -> str:
        return node.name

    def _string_lit(self, node: StringLit) -> str:
        # Use repr() to get proper Python string escaping.
        return repr(node.value)

    def _number_lit(self, node: NumberLit) -> str:
        value = node.value
        # Emit integers without decimal point when the value is whole.
        if value == int(value):
            return str(int(value))
        return str(value)

    def _bool_lit(self, node: BoolLit) -> str:
        return "True" if node.value else "False"

    def _maybe_paren(self, node: Expression, rendered: str) -> str:
        """Wrap *rendered* in parentheses if *node* is a lower-precedence binary op.

        This prevents operator precedence ambiguity in generated code.
        """
        if isinstance(node, BinaryOpExpr) and node.op in (BinOp.AND, BinOp.OR):
            return f"({rendered})"
        return rendered
