"""Unit tests for bsl.schema.json_schema — SchemaExporter and export_schema."""
from __future__ import annotations

import json

import pytest

from bsl.ast.nodes import (
    AgentSpec,
    AppliesTo,
    AuditLevel,
    Behavior,
    BinaryOpExpr,
    BinOp,
    BoolLit,
    Composition,
    Constraint,
    ContainsExpr,
    DotAccess,
    EscalationClause,
    FunctionCall,
    Identifier,
    InListExpr,
    Invariant,
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
from bsl.schema.json_schema import SchemaExporter, export_schema

_S = Span.unknown()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ident(name: str) -> Identifier:
    return Identifier(name=name, span=_S)


def _str_lit(value: str) -> StringLit:
    return StringLit(value=value, span=_S)


def _num_lit(value: float) -> NumberLit:
    return NumberLit(value=value, span=_S)


def _bool_lit(value: bool) -> BoolLit:
    return BoolLit(value=value, span=_S)


def _constraint(name: str) -> Constraint:
    return Constraint(expression=_ident(name), span=_S)


def _should(name: str, pct: float | None = None) -> ShouldConstraint:
    return ShouldConstraint(expression=_ident(name), percentage=pct, span=_S)


def _threshold(op: str, value: float, pct: bool = False) -> ThresholdClause:
    return ThresholdClause(operator=op, value=value, is_percentage=pct, span=_S)


def _behavior(
    name: str,
    *,
    when_clause: object | None = None,
    must: tuple[Constraint, ...] = (),
    must_not: tuple[Constraint, ...] = (),
    should: tuple[ShouldConstraint, ...] = (),
    may: tuple[Constraint, ...] = (),
    confidence: ThresholdClause | None = None,
    latency: ThresholdClause | None = None,
    escalation: EscalationClause | None = None,
    audit: AuditLevel = AuditLevel.NONE,
) -> Behavior:
    return Behavior(
        name=name,
        when_clause=when_clause,  # type: ignore[arg-type]
        must_constraints=must,
        must_not_constraints=must_not,
        should_constraints=should,
        may_constraints=may,
        confidence=confidence,
        latency=latency,
        cost=None,
        escalation=escalation,
        audit=audit,
        span=_S,
    )


def _invariant(
    name: str,
    *,
    applies_to: AppliesTo = AppliesTo.ALL_BEHAVIORS,
    named_behaviors: tuple[str, ...] = (),
    constraints: tuple[Constraint, ...] = (),
    prohibitions: tuple[Constraint, ...] = (),
    severity: Severity = Severity.HIGH,
) -> Invariant:
    return Invariant(
        name=name,
        constraints=constraints,
        prohibitions=prohibitions,
        applies_to=applies_to,
        named_behaviors=named_behaviors,
        severity=severity,
        span=_S,
    )


def _spec(
    name: str = "TestAgent",
    *,
    version: str | None = None,
    model: str | None = None,
    owner: str | None = None,
    behaviors: tuple[Behavior, ...] = (),
    invariants: tuple[Invariant, ...] = (),
) -> AgentSpec:
    return AgentSpec(
        name=name,
        version=version,
        model=model,
        owner=owner,
        behaviors=behaviors,
        invariants=invariants,
        degradations=(),
        compositions=(),
        span=_S,
    )


# ===========================================================================
# SchemaExporter.export — top-level schema structure
# ===========================================================================


class TestSchemaExporterTopLevel:
    def setup_method(self) -> None:
        self.exporter = SchemaExporter()

    def test_schema_version_field(self) -> None:
        schema = self.exporter.export(_spec("A"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"

    def test_schema_id_contains_agent_name(self) -> None:
        schema = self.exporter.export(_spec("CustomerAgent"))
        assert "CustomerAgent" in schema["$id"]

    def test_schema_title_contains_agent_name(self) -> None:
        schema = self.exporter.export(_spec("CustomerAgent"))
        assert "CustomerAgent" in schema["title"]

    def test_schema_type_is_object(self) -> None:
        schema = self.exporter.export(_spec("A"))
        assert schema["type"] == "object"

    def test_required_fields(self) -> None:
        schema = self.exporter.export(_spec("A"))
        assert "agent" in schema["required"]
        assert "behavior" in schema["required"]
        assert "response" in schema["required"]

    def test_additional_properties_false(self) -> None:
        schema = self.exporter.export(_spec("A"))
        assert schema["additionalProperties"] is False

    def test_x_bsl_version_metadata(self) -> None:
        schema = self.exporter.export(_spec("A", version="2.0.0"))
        assert schema["x-bsl-version"] == "2.0.0"

    def test_x_bsl_model_metadata(self) -> None:
        schema = self.exporter.export(_spec("A", model="gpt-4o"))
        assert schema["x-bsl-model"] == "gpt-4o"

    def test_x_bsl_owner_metadata(self) -> None:
        schema = self.exporter.export(_spec("A", owner="team@example.com"))
        assert schema["x-bsl-owner"] == "team@example.com"

    def test_x_bsl_behaviors_is_list(self) -> None:
        schema = self.exporter.export(_spec("A"))
        assert isinstance(schema["x-bsl-behaviors"], list)

    def test_x_bsl_invariants_is_list(self) -> None:
        schema = self.exporter.export(_spec("A"))
        assert isinstance(schema["x-bsl-invariants"], list)

    def test_properties_contains_agent_behavior_response_metadata(self) -> None:
        schema = self.exporter.export(_spec("A"))
        props = schema["properties"]
        assert "agent" in props
        assert "behavior" in props
        assert "response" in props
        assert "metadata" in props

    def test_agent_property_is_const_of_agent_name(self) -> None:
        schema = self.exporter.export(_spec("MyAgent"))
        assert schema["properties"]["agent"]["const"] == "MyAgent"

    def test_behavior_property_enum_contains_behavior_names(self) -> None:
        beh = _behavior("greet")
        schema = self.exporter.export(_spec("A", behaviors=(beh,)))
        enum = schema["properties"]["behavior"]["enum"]
        assert "greet" in enum


# ===========================================================================
# Description building
# ===========================================================================


class TestBuildDescription:
    def setup_method(self) -> None:
        self.exporter = SchemaExporter()

    def test_description_contains_agent_name(self) -> None:
        schema = self.exporter.export(_spec("MyAgent"))
        assert "MyAgent" in schema["description"]

    def test_description_contains_version_when_present(self) -> None:
        schema = self.exporter.export(_spec("A", version="3.0"))
        assert "3.0" in schema["description"]

    def test_description_contains_model_when_present(self) -> None:
        schema = self.exporter.export(_spec("A", model="gpt-4o"))
        assert "gpt-4o" in schema["description"]

    def test_description_contains_owner_when_present(self) -> None:
        schema = self.exporter.export(_spec("A", owner="alice"))
        assert "alice" in schema["description"]

    def test_description_lists_behavior_names(self) -> None:
        spec = _spec("A", behaviors=(_behavior("greet"), _behavior("respond")))
        schema = self.exporter.export(spec)
        assert "greet" in schema["description"]
        assert "respond" in schema["description"]

    def test_description_no_behaviors_message(self) -> None:
        schema = self.exporter.export(_spec("A"))
        assert "No behaviors defined" in schema["description"]


# ===========================================================================
# Response schema
# ===========================================================================


class TestBuildResponseSchema:
    def setup_method(self) -> None:
        self.exporter = SchemaExporter()

    def test_no_behaviors_returns_object_type(self) -> None:
        schema = self.exporter.export(_spec("A"))
        assert schema["properties"]["response"]["type"] == "object"

    def test_with_behaviors_returns_one_of(self) -> None:
        spec = _spec("A", behaviors=(_behavior("greet"),))
        schema = self.exporter.export(spec)
        assert "oneOf" in schema["properties"]["response"]

    def test_behavior_response_contains_content_and_behavior_properties(self) -> None:
        beh = _behavior("greet")
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        behavior_schema = schema["properties"]["response"]["oneOf"][0]
        assert "content" in behavior_schema["properties"]
        assert "behavior" in behavior_schema["properties"]

    def test_behavior_response_includes_confidence_property(self) -> None:
        conf = _threshold(">=", 0.9)
        beh = _behavior("greet", confidence=conf)
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        b_schema = schema["properties"]["response"]["oneOf"][0]
        assert "confidence" in b_schema["properties"]

    def test_behavior_response_includes_latency_property(self) -> None:
        lat = _threshold("<", 500.0)
        beh = _behavior("greet", latency=lat)
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        b_schema = schema["properties"]["response"]["oneOf"][0]
        assert "latency_ms" in b_schema["properties"]

    def test_behavior_response_includes_must_constraints(self) -> None:
        beh = _behavior("greet", must=(_constraint("safe"),))
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        b_schema = schema["properties"]["response"]["oneOf"][0]
        assert "safe" in b_schema["x-bsl-must"]

    def test_behavior_response_includes_must_not_constraints(self) -> None:
        beh = _behavior("greet", must_not=(_constraint("harmful"),))
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        b_schema = schema["properties"]["response"]["oneOf"][0]
        assert "harmful" in b_schema["x-bsl-must_not"]

    def test_behavior_response_includes_should_constraints(self) -> None:
        beh = _behavior("greet", should=(_should("polite", 80.0),))
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        b_schema = schema["properties"]["response"]["oneOf"][0]
        assert len(b_schema["x-bsl-should"]) == 1
        assert b_schema["x-bsl-should"][0]["percentage"] == 80.0

    def test_behavior_response_includes_may_constraints(self) -> None:
        beh = _behavior("greet", may=(_constraint("suggest"),))
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        b_schema = schema["properties"]["response"]["oneOf"][0]
        assert "suggest" in b_schema["x-bsl-may"]

    def test_behavior_response_includes_when_clause(self) -> None:
        beh = _behavior("greet", when_clause=_ident("online"))
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        b_schema = schema["properties"]["response"]["oneOf"][0]
        assert b_schema.get("x-bsl-when") == "online"

    def test_behavior_response_includes_audit_level(self) -> None:
        beh = _behavior("greet", audit=AuditLevel.BASIC)
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        b_schema = schema["properties"]["response"]["oneOf"][0]
        assert b_schema.get("x-bsl-audit") == "basic"

    def test_behavior_response_includes_escalation(self) -> None:
        esc = EscalationClause(condition=_ident("angry"), span=_S)
        beh = _behavior("greet", escalation=esc)
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        b_schema = schema["properties"]["response"]["oneOf"][0]
        assert "angry" in b_schema.get("x-bsl-escalation", "")


# ===========================================================================
# Threshold to schema constraint
# ===========================================================================


class TestThresholdToSchemaConstraint:
    def setup_method(self) -> None:
        self.exporter = SchemaExporter()

    def _get_confidence_schema(self, op: str, value: float, pct: bool = False) -> dict:
        conf = _threshold(op, value, pct)
        beh = _behavior("b", confidence=conf)
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        return schema["properties"]["response"]["oneOf"][0]["properties"]["confidence"]

    def test_less_than_maps_to_exclusive_maximum(self) -> None:
        conf_schema = self._get_confidence_schema("<", 0.95)
        assert "exclusiveMaximum" in conf_schema

    def test_less_than_equal_maps_to_maximum(self) -> None:
        conf_schema = self._get_confidence_schema("<=", 0.95)
        assert "maximum" in conf_schema

    def test_greater_than_maps_to_exclusive_minimum(self) -> None:
        conf_schema = self._get_confidence_schema(">", 0.5)
        assert "exclusiveMinimum" in conf_schema

    def test_greater_than_equal_maps_to_minimum(self) -> None:
        conf_schema = self._get_confidence_schema(">=", 0.9)
        assert "minimum" in conf_schema

    def test_equals_maps_to_const(self) -> None:
        conf_schema = self._get_confidence_schema("==", 0.95)
        assert "const" in conf_schema

    def test_percentage_adds_description_and_bounds(self) -> None:
        conf_schema = self._get_confidence_schema(">=", 90.0, pct=True)
        assert conf_schema["minimum"] == 0.0
        assert conf_schema["maximum"] == 100.0
        assert "description" in conf_schema


# ===========================================================================
# Invariant schema
# ===========================================================================


class TestInvariantToSchema:
    def setup_method(self) -> None:
        self.exporter = SchemaExporter()

    def test_invariant_schema_has_name(self) -> None:
        inv = _invariant("safety")
        spec = _spec("A", invariants=(inv,))
        schema = self.exporter.export(spec)
        inv_schema = schema["x-bsl-invariants"][0]
        assert inv_schema["name"] == "safety"

    def test_invariant_schema_severity_lowercase(self) -> None:
        inv = _invariant("rule", severity=Severity.CRITICAL)
        spec = _spec("A", invariants=(inv,))
        schema = self.exporter.export(spec)
        assert schema["x-bsl-invariants"][0]["severity"] == "critical"

    def test_invariant_applies_to_all_behaviors(self) -> None:
        inv = _invariant("rule", applies_to=AppliesTo.ALL_BEHAVIORS)
        spec = _spec("A", invariants=(inv,))
        schema = self.exporter.export(spec)
        assert schema["x-bsl-invariants"][0]["applies_to"] == "all_behaviors"

    def test_invariant_applies_to_named(self) -> None:
        inv = _invariant(
            "rule",
            applies_to=AppliesTo.NAMED,
            named_behaviors=("respond", "greet"),
        )
        spec = _spec("A", invariants=(inv,))
        schema = self.exporter.export(spec)
        inv_schema = schema["x-bsl-invariants"][0]
        assert set(inv_schema["applies_to"]) == {"respond", "greet"}

    def test_invariant_must_constraints(self) -> None:
        inv = _invariant("rule", constraints=(_constraint("safe"),))
        spec = _spec("A", invariants=(inv,))
        schema = self.exporter.export(spec)
        assert "safe" in schema["x-bsl-invariants"][0]["must"]

    def test_invariant_must_not_constraints(self) -> None:
        inv = _invariant("rule", prohibitions=(_constraint("harmful"),))
        spec = _spec("A", invariants=(inv,))
        schema = self.exporter.export(spec)
        assert "harmful" in schema["x-bsl-invariants"][0]["must_not"]


# ===========================================================================
# Behavior to schema (x-bsl-behaviors)
# ===========================================================================


class TestBehaviorToSchema:
    def setup_method(self) -> None:
        self.exporter = SchemaExporter()

    def test_behavior_summary_has_name(self) -> None:
        beh = _behavior("greet")
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        b_summary = schema["x-bsl-behaviors"][0]
        assert b_summary["name"] == "greet"

    def test_behavior_summary_confidence_format(self) -> None:
        conf = _threshold(">=", 90.0, pct=True)
        beh = _behavior("b", confidence=conf)
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        b_summary = schema["x-bsl-behaviors"][0]
        assert ">=90.0%" in b_summary["confidence"]

    def test_behavior_summary_latency_format(self) -> None:
        lat = _threshold("<", 500.0)
        beh = _behavior("b", latency=lat)
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        b_summary = schema["x-bsl-behaviors"][0]
        assert "<500.0" in b_summary["latency"]

    def test_behavior_summary_audit_lowercase(self) -> None:
        beh = _behavior("b", audit=AuditLevel.FULL_TRACE)
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        assert schema["x-bsl-behaviors"][0]["audit"] == "full_trace"

    def test_behavior_summary_no_confidence_is_none(self) -> None:
        beh = _behavior("b")
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        assert schema["x-bsl-behaviors"][0]["confidence"] is None


# ===========================================================================
# Metadata schema
# ===========================================================================


class TestBuildMetadataSchema:
    def setup_method(self) -> None:
        self.exporter = SchemaExporter()

    def test_metadata_schema_is_object(self) -> None:
        schema = self.exporter.export(_spec("A"))
        meta = schema["properties"]["metadata"]
        assert meta["type"] == "object"

    def test_metadata_schema_has_request_id(self) -> None:
        schema = self.exporter.export(_spec("A"))
        meta = schema["properties"]["metadata"]
        assert "request_id" in meta["properties"]

    def test_metadata_schema_additional_properties_true(self) -> None:
        schema = self.exporter.export(_spec("A"))
        meta = schema["properties"]["metadata"]
        assert meta["additionalProperties"] is True


# ===========================================================================
# to_json
# ===========================================================================


class TestToJson:
    def setup_method(self) -> None:
        self.exporter = SchemaExporter()

    def test_to_json_returns_valid_json(self) -> None:
        spec = _spec("A", version="1.0", model="m")
        json_str = self.exporter.to_json(spec)
        parsed = json.loads(json_str)
        assert parsed["title"].startswith("A")

    def test_to_json_default_indent_is_2(self) -> None:
        spec = _spec("A")
        json_str = self.exporter.to_json(spec)
        # 2-space indent means lines start with "  "
        lines = json_str.split("\n")
        indented = [l for l in lines if l.startswith("  ")]
        assert len(indented) > 0

    def test_to_json_custom_indent(self) -> None:
        spec = _spec("A")
        json_str = self.exporter.to_json(spec, indent=4)
        lines = json_str.split("\n")
        indented_4 = [l for l in lines if l.startswith("    ") and not l.startswith("      ")]
        assert len(indented_4) > 0


# ===========================================================================
# Convenience export_schema function
# ===========================================================================


class TestExportSchemaConvenienceFunction:
    def test_returns_dict(self) -> None:
        spec = _spec("A")
        result = export_schema(spec)
        assert isinstance(result, dict)

    def test_result_matches_exporter_export(self) -> None:
        spec = _spec("A", version="1.0", model="m", owner="o")
        assert export_schema(spec) == SchemaExporter().export(spec)


# ===========================================================================
# _expr_to_description coverage via constraints
# ===========================================================================


class TestExprToDescriptionCoverage:
    """Exercise _expr_to_description through must-constraint schemas."""

    def setup_method(self) -> None:
        self.exporter = SchemaExporter()

    def _must_descriptions(self, *exprs: object) -> list[str]:
        constraints = tuple(
            Constraint(expression=e, span=_S)  # type: ignore[arg-type]
            for e in exprs
        )
        beh = _behavior("b", must=constraints)
        spec = _spec("A", behaviors=(beh,))
        schema = self.exporter.export(spec)
        return schema["properties"]["response"]["oneOf"][0]["x-bsl-must"]

    def test_identifier(self) -> None:
        descs = self._must_descriptions(_ident("safe"))
        assert "safe" in descs

    def test_dot_access(self) -> None:
        descs = self._must_descriptions(DotAccess(parts=("response", "status"), span=_S))
        assert "response.status" in descs

    def test_string_lit(self) -> None:
        descs = self._must_descriptions(_str_lit("hello"))
        assert '"hello"' in descs

    def test_number_lit(self) -> None:
        descs = self._must_descriptions(_num_lit(42.0))
        assert "42.0" in descs

    def test_bool_lit_true(self) -> None:
        descs = self._must_descriptions(_bool_lit(True))
        assert "true" in descs

    def test_binary_op_expr(self) -> None:
        expr = BinaryOpExpr(op=BinOp.AND, left=_ident("a"), right=_ident("b"), span=_S)
        descs = self._must_descriptions(expr)
        assert any("and" in d for d in descs)

    def test_unary_op_expr(self) -> None:
        expr = UnaryOpExpr(op=UnaryOpKind.NOT, operand=_ident("flagged"), span=_S)
        descs = self._must_descriptions(expr)
        assert any("not flagged" in d for d in descs)

    def test_function_call_expr(self) -> None:
        expr = FunctionCall(name="len", arguments=(_ident("items"),), span=_S)
        descs = self._must_descriptions(expr)
        assert any("len(items)" in d for d in descs)

    def test_contains_expr(self) -> None:
        expr = ContainsExpr(subject=_ident("response"), value=_str_lit("error"), span=_S)
        descs = self._must_descriptions(expr)
        assert any("contains" in d for d in descs)

    def test_in_list_expr(self) -> None:
        expr = InListExpr(
            subject=_ident("status"),
            items=(_num_lit(200.0), _num_lit(201.0)),
            span=_S,
        )
        descs = self._must_descriptions(expr)
        assert any("in" in d for d in descs)

    def test_unknown_expr_falls_back_to_repr(self) -> None:
        # Pass a non-Expression object to trigger the fallback repr() branch
        descs = self._must_descriptions(42)
        assert any("42" in d for d in descs)
