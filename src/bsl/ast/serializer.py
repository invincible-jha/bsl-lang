"""AST serialization and deserialization for BSL.

Provides round-trip serialization of ``AgentSpec`` AST trees to and
from JSON and YAML.  The serialized form is a plain dict/list structure
that maps naturally to both formats.

Usage
-----
::

    from bsl.ast.serializer import AstSerializer

    serializer = AstSerializer()
    data = serializer.to_dict(agent_spec)
    json_text = serializer.to_json(agent_spec)
    agent_spec2 = serializer.from_json(json_text)
    assert agent_spec == agent_spec2
"""
from __future__ import annotations

import json

import yaml

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


class AstSerializer:
    """Converts between ``AgentSpec`` AST objects and plain Python dicts.

    The serialized representation uses ``"kind"`` discriminator fields on
    union types so that deserialization is unambiguous.
    """

    # ------------------------------------------------------------------
    # Serialization (AST → dict)
    # ------------------------------------------------------------------

    def to_dict(self, spec: AgentSpec) -> dict[str, object]:
        """Serialize an ``AgentSpec`` to a JSON-compatible dict."""
        return {
            "kind": "AgentSpec",
            "name": spec.name,
            "version": spec.version,
            "model": spec.model,
            "owner": spec.owner,
            "behaviors": [self._behavior_to_dict(b) for b in spec.behaviors],
            "invariants": [self._invariant_to_dict(i) for i in spec.invariants],
            "degradations": [self._degradation_to_dict(d) for d in spec.degradations],
            "compositions": [self._composition_to_dict(c) for c in spec.compositions],
            "span": self._span_to_dict(spec.span),
        }

    def _span_to_dict(self, span: Span) -> dict[str, int]:
        return {"start": span.start, "end": span.end, "line": span.line, "col": span.col}

    def _threshold_to_dict(self, t: ThresholdClause) -> dict[str, object]:
        return {
            "operator": t.operator,
            "value": t.value,
            "is_percentage": t.is_percentage,
            "span": self._span_to_dict(t.span),
        }

    def _escalation_to_dict(self, e: EscalationClause) -> dict[str, object]:
        return {
            "condition": self._expr_to_dict(e.condition),
            "span": self._span_to_dict(e.span),
        }

    def _constraint_to_dict(self, c: Constraint) -> dict[str, object]:
        return {
            "expression": self._expr_to_dict(c.expression),
            "span": self._span_to_dict(c.span),
        }

    def _should_to_dict(self, c: ShouldConstraint) -> dict[str, object]:
        return {
            "expression": self._expr_to_dict(c.expression),
            "percentage": c.percentage,
            "span": self._span_to_dict(c.span),
        }

    def _behavior_to_dict(self, b: Behavior) -> dict[str, object]:
        return {
            "kind": "Behavior",
            "name": b.name,
            "when_clause": self._expr_to_dict(b.when_clause) if b.when_clause else None,
            "must_constraints": [self._constraint_to_dict(c) for c in b.must_constraints],
            "must_not_constraints": [
                self._constraint_to_dict(c) for c in b.must_not_constraints
            ],
            "should_constraints": [self._should_to_dict(c) for c in b.should_constraints],
            "may_constraints": [self._constraint_to_dict(c) for c in b.may_constraints],
            "confidence": self._threshold_to_dict(b.confidence) if b.confidence else None,
            "latency": self._threshold_to_dict(b.latency) if b.latency else None,
            "cost": self._threshold_to_dict(b.cost) if b.cost else None,
            "escalation": self._escalation_to_dict(b.escalation) if b.escalation else None,
            "audit": b.audit.name,
            "span": self._span_to_dict(b.span),
        }

    def _invariant_to_dict(self, i: Invariant) -> dict[str, object]:
        return {
            "kind": "Invariant",
            "name": i.name,
            "constraints": [self._constraint_to_dict(c) for c in i.constraints],
            "prohibitions": [self._constraint_to_dict(c) for c in i.prohibitions],
            "applies_to": i.applies_to.name,
            "named_behaviors": list(i.named_behaviors),
            "severity": i.severity.name,
            "span": self._span_to_dict(i.span),
        }

    def _degradation_to_dict(self, d: Degradation) -> dict[str, object]:
        return {
            "kind": "Degradation",
            "fallback": d.fallback,
            "condition": self._expr_to_dict(d.condition),
            "span": self._span_to_dict(d.span),
        }

    def _composition_to_dict(self, c: Composition) -> dict[str, object]:
        if isinstance(c, Receives):
            return {"kind": "Receives", "source_agent": c.source_agent, "span": self._span_to_dict(c.span)}
        if isinstance(c, Delegates):
            return {"kind": "Delegates", "target_agent": c.target_agent, "span": self._span_to_dict(c.span)}
        raise TypeError(f"Unknown composition type: {type(c)}")

    def _expr_to_dict(self, expr: Expression) -> dict[str, object]:
        if isinstance(expr, Identifier):
            return {"kind": "Identifier", "name": expr.name, "span": self._span_to_dict(expr.span)}
        if isinstance(expr, DotAccess):
            return {"kind": "DotAccess", "parts": list(expr.parts), "span": self._span_to_dict(expr.span)}
        if isinstance(expr, StringLit):
            return {"kind": "StringLit", "value": expr.value, "span": self._span_to_dict(expr.span)}
        if isinstance(expr, NumberLit):
            return {"kind": "NumberLit", "value": expr.value, "span": self._span_to_dict(expr.span)}
        if isinstance(expr, BoolLit):
            return {"kind": "BoolLit", "value": expr.value, "span": self._span_to_dict(expr.span)}
        if isinstance(expr, BinaryOpExpr):
            return {
                "kind": "BinaryOpExpr",
                "op": expr.op.name,
                "left": self._expr_to_dict(expr.left),
                "right": self._expr_to_dict(expr.right),
                "span": self._span_to_dict(expr.span),
            }
        if isinstance(expr, UnaryOpExpr):
            return {
                "kind": "UnaryOpExpr",
                "op": expr.op.name,
                "operand": self._expr_to_dict(expr.operand),
                "span": self._span_to_dict(expr.span),
            }
        if isinstance(expr, FunctionCall):
            return {
                "kind": "FunctionCall",
                "name": expr.name,
                "arguments": [self._expr_to_dict(a) for a in expr.arguments],
                "span": self._span_to_dict(expr.span),
            }
        if isinstance(expr, ContainsExpr):
            return {
                "kind": "ContainsExpr",
                "subject": self._expr_to_dict(expr.subject),
                "value": self._expr_to_dict(expr.value),
                "span": self._span_to_dict(expr.span),
            }
        if isinstance(expr, InListExpr):
            return {
                "kind": "InListExpr",
                "subject": self._expr_to_dict(expr.subject),
                "items": [self._expr_to_dict(i) for i in expr.items],
                "span": self._span_to_dict(expr.span),
            }
        if isinstance(expr, BeforeExpr):
            return {
                "kind": "BeforeExpr",
                "left": self._expr_to_dict(expr.left),
                "right": self._expr_to_dict(expr.right),
                "span": self._span_to_dict(expr.span),
            }
        if isinstance(expr, AfterExpr):
            return {
                "kind": "AfterExpr",
                "left": self._expr_to_dict(expr.left),
                "right": self._expr_to_dict(expr.right),
                "span": self._span_to_dict(expr.span),
            }
        raise TypeError(f"Unknown expression type: {type(expr)}")

    # ------------------------------------------------------------------
    # Deserialization (dict → AST)
    # ------------------------------------------------------------------

    def from_dict(self, data: dict[str, object]) -> AgentSpec:
        """Deserialize an ``AgentSpec`` from a plain dict."""
        return AgentSpec(
            name=data["name"],
            version=data.get("version"),
            model=data.get("model"),
            owner=data.get("owner"),
            behaviors=tuple(self._behavior_from_dict(b) for b in data.get("behaviors", [])),
            invariants=tuple(self._invariant_from_dict(i) for i in data.get("invariants", [])),
            degradations=tuple(
                self._degradation_from_dict(d) for d in data.get("degradations", [])
            ),
            compositions=tuple(
                self._composition_from_dict(c) for c in data.get("compositions", [])
            ),
            span=self._span_from_dict(data["span"]),
        )

    def _span_from_dict(self, d: dict[str, int]) -> Span:
        return Span(start=d["start"], end=d["end"], line=d["line"], col=d["col"])

    def _threshold_from_dict(self, d: dict[str, object]) -> ThresholdClause:
        return ThresholdClause(
            operator=d["operator"],
            value=float(d["value"]),
            is_percentage=bool(d.get("is_percentage", False)),
            span=self._span_from_dict(d["span"]),
        )

    def _escalation_from_dict(self, d: dict[str, object]) -> EscalationClause:
        return EscalationClause(
            condition=self._expr_from_dict(d["condition"]),
            span=self._span_from_dict(d["span"]),
        )

    def _constraint_from_dict(self, d: dict[str, object]) -> Constraint:
        return Constraint(
            expression=self._expr_from_dict(d["expression"]),
            span=self._span_from_dict(d["span"]),
        )

    def _should_from_dict(self, d: dict[str, object]) -> ShouldConstraint:
        return ShouldConstraint(
            expression=self._expr_from_dict(d["expression"]),
            percentage=d.get("percentage"),
            span=self._span_from_dict(d["span"]),
        )

    def _behavior_from_dict(self, d: dict[str, object]) -> Behavior:
        return Behavior(
            name=d["name"],
            when_clause=self._expr_from_dict(d["when_clause"]) if d.get("when_clause") else None,
            must_constraints=tuple(self._constraint_from_dict(c) for c in d.get("must_constraints", [])),
            must_not_constraints=tuple(
                self._constraint_from_dict(c) for c in d.get("must_not_constraints", [])
            ),
            should_constraints=tuple(
                self._should_from_dict(c) for c in d.get("should_constraints", [])
            ),
            may_constraints=tuple(self._constraint_from_dict(c) for c in d.get("may_constraints", [])),
            confidence=self._threshold_from_dict(d["confidence"]) if d.get("confidence") else None,
            latency=self._threshold_from_dict(d["latency"]) if d.get("latency") else None,
            cost=self._threshold_from_dict(d["cost"]) if d.get("cost") else None,
            escalation=self._escalation_from_dict(d["escalation"]) if d.get("escalation") else None,
            audit=AuditLevel[d.get("audit", "NONE")],
            span=self._span_from_dict(d["span"]),
        )

    def _invariant_from_dict(self, d: dict[str, object]) -> Invariant:
        return Invariant(
            name=d["name"],
            constraints=tuple(self._constraint_from_dict(c) for c in d.get("constraints", [])),
            prohibitions=tuple(self._constraint_from_dict(c) for c in d.get("prohibitions", [])),
            applies_to=AppliesTo[d.get("applies_to", "ALL_BEHAVIORS")],
            named_behaviors=tuple(d.get("named_behaviors", [])),
            severity=Severity[d.get("severity", "HIGH")],
            span=self._span_from_dict(d["span"]),
        )

    def _degradation_from_dict(self, d: dict[str, object]) -> Degradation:
        return Degradation(
            fallback=d["fallback"],
            condition=self._expr_from_dict(d["condition"]),
            span=self._span_from_dict(d["span"]),
        )

    def _composition_from_dict(self, d: dict[str, object]) -> Composition:
        kind = d["kind"]
        if kind == "Receives":
            return Receives(source_agent=d["source_agent"], span=self._span_from_dict(d["span"]))
        if kind == "Delegates":
            return Delegates(target_agent=d["target_agent"], span=self._span_from_dict(d["span"]))
        raise ValueError(f"Unknown composition kind: {kind!r}")

    def _expr_from_dict(self, d: dict[str, object]) -> Expression:
        kind = d["kind"]
        span = self._span_from_dict(d["span"])
        if kind == "Identifier":
            return Identifier(name=d["name"], span=span)
        if kind == "DotAccess":
            return DotAccess(parts=tuple(d["parts"]), span=span)
        if kind == "StringLit":
            return StringLit(value=d["value"], span=span)
        if kind == "NumberLit":
            return NumberLit(value=float(d["value"]), span=span)
        if kind == "BoolLit":
            return BoolLit(value=bool(d["value"]), span=span)
        if kind == "BinaryOpExpr":
            return BinaryOpExpr(
                op=BinOp[d["op"]],
                left=self._expr_from_dict(d["left"]),
                right=self._expr_from_dict(d["right"]),
                span=span,
            )
        if kind == "UnaryOpExpr":
            return UnaryOpExpr(
                op=UnaryOpKind[d["op"]],
                operand=self._expr_from_dict(d["operand"]),
                span=span,
            )
        if kind == "FunctionCall":
            return FunctionCall(
                name=d["name"],
                arguments=tuple(self._expr_from_dict(a) for a in d.get("arguments", [])),
                span=span,
            )
        if kind == "ContainsExpr":
            return ContainsExpr(
                subject=self._expr_from_dict(d["subject"]),
                value=self._expr_from_dict(d["value"]),
                span=span,
            )
        if kind == "InListExpr":
            return InListExpr(
                subject=self._expr_from_dict(d["subject"]),
                items=tuple(self._expr_from_dict(i) for i in d.get("items", [])),
                span=span,
            )
        if kind == "BeforeExpr":
            return BeforeExpr(
                left=self._expr_from_dict(d["left"]),
                right=self._expr_from_dict(d["right"]),
                span=span,
            )
        if kind == "AfterExpr":
            return AfterExpr(
                left=self._expr_from_dict(d["left"]),
                right=self._expr_from_dict(d["right"]),
                span=span,
            )
        raise ValueError(f"Unknown expression kind: {kind!r}")

    # ------------------------------------------------------------------
    # JSON helpers
    # ------------------------------------------------------------------

    def to_json(self, spec: AgentSpec, indent: int = 2) -> str:
        """Serialize an ``AgentSpec`` to a JSON string."""
        return json.dumps(self.to_dict(spec), indent=indent, ensure_ascii=False)

    def from_json(self, text: str) -> AgentSpec:
        """Deserialize an ``AgentSpec`` from a JSON string."""
        data: dict[str, object] = json.loads(text)
        return self.from_dict(data)

    # ------------------------------------------------------------------
    # YAML helpers
    # ------------------------------------------------------------------

    def to_yaml(self, spec: AgentSpec) -> str:
        """Serialize an ``AgentSpec`` to a YAML string."""
        return yaml.dump(self.to_dict(spec), default_flow_style=False, allow_unicode=True)

    def from_yaml(self, text: str) -> AgentSpec:
        """Deserialize an ``AgentSpec`` from a YAML string."""
        data: dict[str, object] = yaml.safe_load(text)
        return self.from_dict(data)
