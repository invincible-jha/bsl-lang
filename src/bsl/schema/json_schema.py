"""JSON Schema exporter for BSL agent specifications.

``SchemaExporter`` converts a BSL ``AgentSpec`` into a JSON Schema
(draft 2020-12) document that can validate agent behavior at runtime.
The generated schema encodes:

- Allowed behavior names (as an enum)
- Required properties for each behavior's output
- Confidence, latency, and cost thresholds as numeric constraints
- Must / must_not / should constraints as description annotations
  (since JSON Schema cannot fully express arbitrary BSL expressions,
  constraint text is embedded in ``description`` fields for tooling)
- Invariant severity levels
- Audit requirements

The schema is intended to be used as documentation-as-code and for
runtime validation of structured LLM outputs.

Usage
-----
::

    from bsl.schema import SchemaExporter
    from bsl.parser import parse

    spec = parse(source)
    exporter = SchemaExporter()
    schema = exporter.export(spec)
    import json
    print(json.dumps(schema, indent=2))
"""
from __future__ import annotations

import json

from bsl.ast.nodes import (
    AgentSpec,
    AppliesTo,
    AuditLevel,
    Behavior,
    BinaryOpExpr,
    BoolLit,
    Constraint,
    ContainsExpr,
    DotAccess,
    Expression,
    FunctionCall,
    Identifier,
    InListExpr,
    Invariant,
    NumberLit,
    ShouldConstraint,
    StringLit,
    ThresholdClause,
    UnaryOpExpr,
)

Schema = dict[str, object]


def _expr_to_description(expr: Expression) -> str:
    """Produce a human-readable description string from an expression."""
    if isinstance(expr, Identifier):
        return expr.name
    if isinstance(expr, DotAccess):
        return ".".join(expr.parts)
    if isinstance(expr, StringLit):
        return f'"{expr.value}"'
    if isinstance(expr, NumberLit):
        return str(expr.value)
    if isinstance(expr, BoolLit):
        return str(expr.value).lower()
    if isinstance(expr, BinaryOpExpr):
        left = _expr_to_description(expr.left)
        right = _expr_to_description(expr.right)
        return f"{left} {expr.op.name.lower()} {right}"
    if isinstance(expr, UnaryOpExpr):
        return f"not {_expr_to_description(expr.operand)}"
    if isinstance(expr, FunctionCall):
        args = ", ".join(_expr_to_description(a) for a in expr.arguments)
        return f"{expr.name}({args})"
    if isinstance(expr, ContainsExpr):
        return f"{_expr_to_description(expr.subject)} contains {_expr_to_description(expr.value)}"
    if isinstance(expr, InListExpr):
        items = ", ".join(_expr_to_description(i) for i in expr.items)
        return f"{_expr_to_description(expr.subject)} in [{items}]"
    return repr(expr)


def _threshold_to_schema_constraint(t: ThresholdClause, prop_name: str) -> Schema:
    """Convert a threshold clause to a JSON Schema numeric constraint."""
    schema: Schema = {"type": "number"}
    op_map = {
        "<": "exclusiveMaximum",
        "<=": "maximum",
        ">": "exclusiveMinimum",
        ">=": "minimum",
    }
    if t.operator in op_map:
        schema[op_map[t.operator]] = t.value
    elif t.operator == "==":
        schema["const"] = t.value
    if t.is_percentage:
        schema["description"] = f"{prop_name} as a percentage value in [0, 100]"
        schema["minimum"] = 0.0
        schema["maximum"] = 100.0
    return schema


class SchemaExporter:
    """Converts a BSL ``AgentSpec`` to a JSON Schema document.

    The generated schema can be used to:
    1. Validate structured LLM output against behavioral specifications
    2. Generate documentation for agent behavior
    3. Power IDE tooling and autocomplete
    """

    def export(self, spec: AgentSpec) -> Schema:
        """Generate a JSON Schema from an ``AgentSpec``.

        Parameters
        ----------
        spec:
            The agent specification to convert.

        Returns
        -------
        Schema
            A JSON Schema (draft 2020-12) dict representing the agent spec.
        """
        schema: Schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"https://bsl-lang.io/schemas/agents/{spec.name}",
            "title": f"{spec.name} — BSL Agent Specification",
            "description": self._build_description(spec),
            "type": "object",
            "properties": {
                "agent": {"const": spec.name},
                "behavior": {
                    "type": "string",
                    "enum": sorted(b.name for b in spec.behaviors),
                    "description": "The behavior being invoked",
                },
                "response": self._build_response_schema(spec),
                "metadata": self._build_metadata_schema(spec),
            },
            "required": ["agent", "behavior", "response"],
            "additionalProperties": False,
            "x-bsl-version": spec.version,
            "x-bsl-model": spec.model,
            "x-bsl-owner": spec.owner,
            "x-bsl-behaviors": [
                self._behavior_to_schema(b, spec) for b in spec.behaviors
            ],
            "x-bsl-invariants": [
                self._invariant_to_schema(i) for i in spec.invariants
            ],
        }
        return schema

    def to_json(self, spec: AgentSpec, indent: int = 2) -> str:
        """Export the spec as a JSON string.

        Parameters
        ----------
        spec:
            The agent specification to convert.
        indent:
            JSON indentation level.

        Returns
        -------
        str
            Formatted JSON schema string.
        """
        return json.dumps(self.export(spec), indent=indent, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_description(self, spec: AgentSpec) -> str:
        parts = [f"BSL Agent: {spec.name}"]
        if spec.version:
            parts.append(f"Version: {spec.version}")
        if spec.model:
            parts.append(f"Model: {spec.model}")
        if spec.owner:
            parts.append(f"Owner: {spec.owner}")
        parts.append(
            f"Behaviors: {', '.join(b.name for b in spec.behaviors)}"
            if spec.behaviors else "No behaviors defined"
        )
        return " | ".join(parts)

    def _build_response_schema(self, spec: AgentSpec) -> Schema:
        """Build a oneOf schema that covers each behavior's response shape."""
        if not spec.behaviors:
            return {"type": "object"}

        return {
            "oneOf": [self._behavior_response_schema(b) for b in spec.behaviors],
            "description": "The agent's response, shape varies by behavior",
        }

    def _behavior_response_schema(self, b: Behavior) -> Schema:
        """Build the response schema for a single behavior."""
        properties: Schema = {
            "content": {"type": "string", "description": "The primary response text"},
            "behavior": {"const": b.name},
        }

        # Add confidence property if threshold defined
        if b.confidence is not None:
            properties["confidence"] = _threshold_to_schema_constraint(
                b.confidence, "confidence"
            )

        # Add latency (for documentation only — can't validate timing in JSON Schema)
        if b.latency is not None:
            properties["latency_ms"] = {
                "type": "number",
                **_threshold_to_schema_constraint(b.latency, "latency_ms"),
                "description": f"Response latency in ms; target: {b.latency.operator}{b.latency.value}",
            }

        schema: Schema = {
            "type": "object",
            "title": f"Response for behavior '{b.name}'",
            "properties": properties,
            "required": ["content", "behavior"],
            "x-bsl-must": [_expr_to_description(c.expression) for c in b.must_constraints],
            "x-bsl-must_not": [_expr_to_description(c.expression) for c in b.must_not_constraints],
            "x-bsl-should": [
                {
                    "expression": _expr_to_description(c.expression),
                    "percentage": c.percentage,
                }
                for c in b.should_constraints
            ],
            "x-bsl-may": [_expr_to_description(c.expression) for c in b.may_constraints],
        }

        if b.when_clause:
            schema["x-bsl-when"] = _expr_to_description(b.when_clause)
        if b.audit != AuditLevel.NONE:
            schema["x-bsl-audit"] = b.audit.name.lower()
        if b.escalation:
            schema["x-bsl-escalation"] = _expr_to_description(b.escalation.condition)

        return schema

    def _build_metadata_schema(self, spec: AgentSpec) -> Schema:
        """Build a schema for the optional request metadata object."""
        return {
            "type": "object",
            "properties": {
                "request_id": {"type": "string"},
                "user_id": {"type": "string"},
                "session_id": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
                "trace_id": {"type": "string"},
            },
            "additionalProperties": True,
            "description": "Optional request metadata for tracing and audit",
        }

    def _behavior_to_schema(self, b: Behavior, spec: AgentSpec) -> Schema:
        """Produce a compact behavior summary for the x-bsl-behaviors extension."""
        return {
            "name": b.name,
            "when": _expr_to_description(b.when_clause) if b.when_clause else None,
            "must": [_expr_to_description(c.expression) for c in b.must_constraints],
            "must_not": [_expr_to_description(c.expression) for c in b.must_not_constraints],
            "should": [
                {"expr": _expr_to_description(c.expression), "pct": c.percentage}
                for c in b.should_constraints
            ],
            "may": [_expr_to_description(c.expression) for c in b.may_constraints],
            "confidence": (
                f"{b.confidence.operator}{b.confidence.value}"
                + ("%" if b.confidence.is_percentage else "")
            ) if b.confidence else None,
            "latency": (
                f"{b.latency.operator}{b.latency.value}"
            ) if b.latency else None,
            "audit": b.audit.name.lower(),
        }

    def _invariant_to_schema(self, inv: Invariant) -> Schema:
        """Produce a compact invariant summary for the x-bsl-invariants extension."""
        return {
            "name": inv.name,
            "severity": inv.severity.name.lower(),
            "applies_to": (
                "all_behaviors"
                if inv.applies_to == AppliesTo.ALL_BEHAVIORS
                else list(inv.named_behaviors)
            ),
            "must": [_expr_to_description(c.expression) for c in inv.constraints],
            "must_not": [_expr_to_description(c.expression) for c in inv.prohibitions],
        }


def export_schema(spec: AgentSpec) -> Schema:
    """Convenience function: export an ``AgentSpec`` as a JSON Schema dict.

    Parameters
    ----------
    spec:
        The agent specification to export.

    Returns
    -------
    Schema
        A JSON Schema (draft 2020-12) dict.
    """
    return SchemaExporter().export(spec)
