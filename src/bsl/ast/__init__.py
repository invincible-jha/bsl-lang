"""BSL AST module.

Exports all AST node types and the serializer for converting AST trees
to and from JSON/YAML.
"""
from __future__ import annotations

from bsl.ast.nodes import (
    AfterExpr,
    AgentSpec,
    AppliesTo,
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
    Literal,
    NumberLit,
    Receives,
    Severity,
    ShouldConstraint,
    Span,
    StringLit,
    ThresholdClause,
    UnaryOpExpr,
    UnaryOpKind,
)
from bsl.ast.serializer import AstSerializer

__all__ = [
    # Core node types
    "Span",
    "AgentSpec",
    "Behavior",
    "Constraint",
    "ShouldConstraint",
    "Invariant",
    "Degradation",
    "Composition",
    "Receives",
    "Delegates",
    "ThresholdClause",
    "EscalationClause",
    # Enums
    "AppliesTo",
    "Severity",
    "AuditLevel",
    "BinOp",
    "UnaryOpKind",
    # Expression types
    "Expression",
    "Identifier",
    "DotAccess",
    "Literal",
    "StringLit",
    "NumberLit",
    "BoolLit",
    "BinaryOpExpr",
    "UnaryOpExpr",
    "FunctionCall",
    "ContainsExpr",
    "InListExpr",
    "BeforeExpr",
    "AfterExpr",
    # Serializer
    "AstSerializer",
]
