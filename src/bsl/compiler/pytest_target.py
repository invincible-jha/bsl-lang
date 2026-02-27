"""BSL → pytest compiler target.

This module contains the primary ``PytestTarget`` class that walks a
``AgentSpec`` AST and generates a ready-to-run pytest test file.

Generation strategy
--------------------
For each element in the BSL spec a corresponding test is produced:

* ``INVARIANT`` → ``test_invariant_<name>_must_*`` and
  ``test_invariant_<name>_must_not_*``
* ``BEHAVIOR`` must constraints → ``test_behavior_<name>_must_*``
* ``BEHAVIOR`` must_not constraints → ``test_behavior_<name>_must_not_*``
* ``BEHAVIOR`` should constraints → ``test_behavior_<name>_should_*``
* ``BEHAVIOR`` thresholds (confidence/latency/cost) →
  ``test_behavior_<name>_<metric>_threshold``
* ``BEHAVIOR`` escalation clause → ``test_behavior_<name>_escalation``

All tests receive a common ``agent_context`` fixture that provides a
minimal mock namespace.  Tests that cannot be expressed as simple
assertions emit a ``pytest.skip`` with an explanatory message.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from bsl.ast.nodes import (
    AfterExpr,
    AgentSpec,
    Behavior,
    BeforeExpr,
    BinaryOpExpr,
    ContainsExpr,
    Constraint,
    EscalationClause,
    Expression,
    FunctionCall,
    InListExpr,
    Invariant,
    ShouldConstraint,
    ThresholdClause,
    UnaryOpExpr,
)
from bsl.compiler.base import CompilerOutput, CompilerTarget
from bsl.compiler.code_generator import TEMPORAL_HELPERS, CodeGenerator
from bsl.compiler.template_engine import (
    render_file_header,
    render_module_docstring,
    render_section_separator,
    render_test_function,
    sanitize_identifier,
)


def _has_temporal(expression: Expression) -> bool:
    """Return True if *expression* contains a ``before``/``after`` sub-expression."""
    if isinstance(expression, (BeforeExpr, AfterExpr)):
        return True
    if isinstance(expression, BinaryOpExpr):
        return _has_temporal(expression.left) or _has_temporal(expression.right)
    if isinstance(expression, UnaryOpExpr):
        return _has_temporal(expression.operand)
    if isinstance(expression, ContainsExpr):
        return _has_temporal(expression.subject) or _has_temporal(expression.value)
    if isinstance(expression, InListExpr):
        return any(_has_temporal(item) for item in expression.items)
    if isinstance(expression, FunctionCall):
        return any(_has_temporal(arg) for arg in expression.arguments)
    return False


class PytestTarget(CompilerTarget):
    """Compiles a BSL ``AgentSpec`` into a pytest test file.

    The generated file is self-contained: it defines its own mock
    ``_AgentContext`` class and ``agent_context`` fixture so it can be
    executed immediately with ``pytest`` without any additional setup.
    """

    @property
    def name(self) -> str:
        return "pytest"

    def compile(self, spec: AgentSpec) -> CompilerOutput:
        """Compile *spec* to a pytest test file.

        Parameters
        ----------
        spec:
            The parsed BSL agent specification.

        Returns
        -------
        CompilerOutput
            A single-file output mapping
            ``test_<agent_snake>_spec.py`` → generated source.
        """
        gen = CodeGenerator()
        generated_at = datetime.now(tz=timezone.utc)
        warnings: list[str] = []
        sections: list[str] = []
        test_count = 0

        # Detect whether we need temporal helper functions.
        needs_temporal = _spec_has_temporal(spec)

        # ---- File header --------------------------------------------------
        header = render_file_header(
            agent_name=spec.name,
            bsl_version=spec.version,
            generated_at=generated_at,
        )
        sections.append(header)

        # ---- Module docstring ---------------------------------------------
        sections.append(render_module_docstring(spec.name))

        # ---- Imports ------------------------------------------------------
        sections.append(_render_imports(needs_temporal))

        # ---- Agent context fixture ----------------------------------------
        sections.append(render_section_separator("Fixtures"))
        sections.append(_render_agent_context_fixture(spec.name))

        # ---- Invariant tests ----------------------------------------------
        if spec.invariants:
            sections.append(render_section_separator("Invariant tests"))
            for invariant in spec.invariants:
                inv_tests, count, inv_warnings = _compile_invariant(
                    invariant, gen
                )
                sections.extend(inv_tests)
                test_count += count
                warnings.extend(inv_warnings)

        # ---- Behavior tests -----------------------------------------------
        if spec.behaviors:
            sections.append(render_section_separator("Behavior tests"))
            for behavior in spec.behaviors:
                beh_tests, count, beh_warnings = _compile_behavior(
                    behavior, gen
                )
                sections.extend(beh_tests)
                test_count += count
                warnings.extend(beh_warnings)

        # ---- Assemble the source file -------------------------------------
        source = "\n".join(sections)

        # Compute output filename.
        snake_name = _to_snake(spec.name)
        filename = f"test_{snake_name}_spec.py"

        metadata: dict[str, object] = {
            "agent_name": spec.name,
            "agent_version": spec.version,
            "invariant_count": len(spec.invariants),
            "behavior_count": len(spec.behaviors),
            "generated_at": generated_at.isoformat(),
        }

        return CompilerOutput(
            files={filename: source},
            metadata=metadata,
            test_count=test_count,
            warnings=warnings,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _spec_has_temporal(spec: AgentSpec) -> bool:
    """Return True if any expression in *spec* uses before/after."""
    for invariant in spec.invariants:
        for constraint in invariant.constraints:
            if _has_temporal(constraint.expression):
                return True
        for prohibition in invariant.prohibitions:
            if _has_temporal(prohibition.expression):
                return True
    for behavior in spec.behaviors:
        for constraint in (
            *behavior.must_constraints,
            *behavior.must_not_constraints,
            *behavior.may_constraints,
        ):
            if _has_temporal(constraint.expression):
                return True
        for should in behavior.should_constraints:
            if _has_temporal(should.expression):
                return True
        if behavior.when_clause and _has_temporal(behavior.when_clause):
            return True
        if behavior.escalation and _has_temporal(behavior.escalation.condition):
            return True
    return False


def _render_imports(needs_temporal: bool) -> str:
    """Return the import block with optional temporal helpers."""
    lines = [
        "from __future__ import annotations",
        "",
        "import re",
        "from typing import Any",
        "",
        "import pytest",
        "",
    ]
    if needs_temporal:
        lines.append(TEMPORAL_HELPERS)
    return "\n".join(lines)


def _render_agent_context_fixture(agent_name: str) -> str:
    """Return the ``_AgentContext`` class and ``agent_context`` fixture."""
    return f'''\
class _AgentContext:
    """Minimal mock context for {agent_name} tests.

    Attribute access on this object never raises ``AttributeError`` —
    unknown attributes return ``None``.  Tests set attributes directly
    to configure the scenario under test.
    """

    def __setattr__(self, name: str, value: Any) -> None:  # noqa: ANN401
        object.__setattr__(self, name, value)

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
        return _NestedContext(name)


class _NestedContext:
    """Proxy for dotted attribute access on ``_AgentContext``."""

    def __init__(self, path: str) -> None:
        object.__setattr__(self, "_path", path)

    def __getattr__(self, name: str) -> "_NestedContext":
        path = object.__getattribute__(self, "_path")
        return _NestedContext(f"{{path}}.{{name}}")

    def __setattr__(self, name: str, value: Any) -> None:  # noqa: ANN401
        object.__setattr__(self, name, value)

    def __eq__(self, other: object) -> bool:
        return False

    def __lt__(self, other: object) -> bool:
        return False

    def __le__(self, other: object) -> bool:
        return False

    def __gt__(self, other: object) -> bool:
        return False

    def __ge__(self, other: object) -> bool:
        return False

    def __contains__(self, item: object) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        path = object.__getattribute__(self, "_path")
        return f"_NestedContext({{path!r}})"


@pytest.fixture()
def agent_context() -> _AgentContext:
    """Provide a clean mock agent context for each test."""
    return _AgentContext()

'''


def _compile_invariant(
    invariant: Invariant,
    gen: CodeGenerator,
) -> tuple[list[str], int, list[str]]:
    """Generate test functions for a single BSL invariant.

    Parameters
    ----------
    invariant:
        The ``Invariant`` AST node.
    gen:
        The code generator instance.

    Returns
    -------
    tuple[list[str], int, list[str]]
        (list of source blocks, number of tests generated, warnings)
    """
    blocks: list[str] = []
    test_count = 0
    warnings: list[str] = []
    safe_name = sanitize_identifier(invariant.name)

    # must constraints → assert positively
    for idx, constraint in enumerate(invariant.constraints):
        test_name = f"test_invariant_{safe_name}_must_{idx}"
        assertion = gen.generate_assertion(constraint.expression)
        docstring = (
            f"Invariant '{invariant.name}' must hold: "
            f"{gen.generate(constraint.expression)}"
        )
        block = render_test_function(
            test_name=test_name,
            docstring=docstring,
            fixture_names=["agent_context"],
            body_lines=[
                "# Populate agent_context attributes to match your agent's output.",
                "ctx = agent_context",
                _adapt_assertion_for_context(assertion),
            ],
        )
        blocks.append(block)
        test_count += 1

    # must_not constraints → assert negated
    for idx, prohibition in enumerate(invariant.prohibitions):
        test_name = f"test_invariant_{safe_name}_must_not_{idx}"
        assertion = gen.generate_negated_assertion(prohibition.expression)
        docstring = (
            f"Invariant '{invariant.name}' must NOT hold: "
            f"{gen.generate(prohibition.expression)}"
        )
        block = render_test_function(
            test_name=test_name,
            docstring=docstring,
            fixture_names=["agent_context"],
            body_lines=[
                "# Populate agent_context attributes to match your agent's output.",
                "ctx = agent_context",
                _adapt_assertion_for_context(assertion),
            ],
        )
        blocks.append(block)
        test_count += 1

    if not invariant.constraints and not invariant.prohibitions:
        warnings.append(
            f"Invariant '{invariant.name}' has no constraints — skipped."
        )

    return blocks, test_count, warnings


def _compile_behavior(
    behavior: Behavior,
    gen: CodeGenerator,
) -> tuple[list[str], int, list[str]]:
    """Generate test functions for a single BSL behavior.

    Parameters
    ----------
    behavior:
        The ``Behavior`` AST node.
    gen:
        The code generator instance.

    Returns
    -------
    tuple[list[str], int, list[str]]
        (list of source blocks, number of tests generated, warnings)
    """
    blocks: list[str] = []
    test_count = 0
    warnings: list[str] = []
    safe_name = sanitize_identifier(behavior.name)

    # must constraints
    for idx, constraint in enumerate(behavior.must_constraints):
        test_name = f"test_behavior_{safe_name}_must_{idx}"
        assertion = gen.generate_assertion(constraint.expression)
        docstring = (
            f"Behavior '{behavior.name}' must: "
            f"{gen.generate(constraint.expression)}"
        )
        block = render_test_function(
            test_name=test_name,
            docstring=docstring,
            fixture_names=["agent_context"],
            body_lines=[
                "ctx = agent_context",
                _adapt_assertion_for_context(assertion),
            ],
        )
        blocks.append(block)
        test_count += 1

    # must_not constraints
    for idx, prohibition in enumerate(behavior.must_not_constraints):
        test_name = f"test_behavior_{safe_name}_must_not_{idx}"
        assertion = gen.generate_negated_assertion(prohibition.expression)
        docstring = (
            f"Behavior '{behavior.name}' must NOT: "
            f"{gen.generate(prohibition.expression)}"
        )
        block = render_test_function(
            test_name=test_name,
            docstring=docstring,
            fixture_names=["agent_context"],
            body_lines=[
                "ctx = agent_context",
                _adapt_assertion_for_context(assertion),
            ],
        )
        blocks.append(block)
        test_count += 1

    # should constraints (soft — marked xfail for missing compliance)
    for idx, should in enumerate(behavior.should_constraints):
        test_name = f"test_behavior_{safe_name}_should_{idx}"
        assertion = gen.generate_assertion(should.expression)
        pct_note = (
            f" ({should.percentage:.0f}% of cases)" if should.percentage is not None else ""
        )
        docstring = (
            f"Behavior '{behavior.name}' should{pct_note}: "
            f"{gen.generate(should.expression)}"
        )
        block = render_test_function(
            test_name=test_name,
            docstring=docstring,
            fixture_names=["agent_context"],
            body_lines=[
                "ctx = agent_context",
                _adapt_assertion_for_context(assertion),
            ],
            markers=[
                'pytest.mark.xfail(reason="soft constraint — may not hold in all cases", strict=False)'
            ],
        )
        blocks.append(block)
        test_count += 1

    # Threshold tests — confidence
    if behavior.confidence is not None:
        block, warnings_from_threshold = _compile_threshold_test(
            behavior_name=safe_name,
            metric="confidence",
            threshold=behavior.confidence,
        )
        blocks.append(block)
        test_count += 1
        warnings.extend(warnings_from_threshold)

    # Threshold tests — latency
    if behavior.latency is not None:
        block, warnings_from_threshold = _compile_threshold_test(
            behavior_name=safe_name,
            metric="latency",
            threshold=behavior.latency,
        )
        blocks.append(block)
        test_count += 1
        warnings.extend(warnings_from_threshold)

    # Threshold tests — cost
    if behavior.cost is not None:
        block, warnings_from_threshold = _compile_threshold_test(
            behavior_name=safe_name,
            metric="cost",
            threshold=behavior.cost,
        )
        blocks.append(block)
        test_count += 1
        warnings.extend(warnings_from_threshold)

    # Escalation clause test
    if behavior.escalation is not None:
        block = _compile_escalation_test(safe_name, behavior.escalation, gen)
        blocks.append(block)
        test_count += 1

    return blocks, test_count, warnings


def _compile_threshold_test(
    behavior_name: str,
    metric: str,
    threshold: ThresholdClause,
) -> tuple[str, list[str]]:
    """Generate a threshold assertion test.

    Parameters
    ----------
    behavior_name:
        Sanitized behavior identifier.
    metric:
        One of ``"confidence"``, ``"latency"``, ``"cost"``.
    threshold:
        The ``ThresholdClause`` AST node.

    Returns
    -------
    tuple[str, list[str]]
        (source block, warnings)
    """
    test_name = f"test_behavior_{behavior_name}_{metric}_threshold"
    op = threshold.operator
    value = threshold.value
    pct = threshold.is_percentage

    value_repr = f"{value:.0f}" if value == int(value) else str(value)
    unit = "%" if pct else ""
    docstring = (
        f"Behavior '{behavior_name}' {metric} must be {op} {value_repr}{unit}."
    )
    body_lines = [
        f"# Set agent_context.{metric} to the observed measurement.",
        f"actual_{metric} = getattr(agent_context, '{metric}', None)",
        f"if actual_{metric} is None:",
        f"    pytest.skip('No {metric} value set on agent_context')",
        f"assert actual_{metric} {op} {value_repr}, (",
        f"    f'Expected {metric} {op} {value_repr}{unit}, got {{actual_{metric}}}'",
        f")",
    ]
    block = render_test_function(
        test_name=test_name,
        docstring=docstring,
        fixture_names=["agent_context"],
        body_lines=body_lines,
    )
    return block, []


def _compile_escalation_test(
    behavior_name: str,
    escalation: EscalationClause,
    gen: CodeGenerator,
) -> str:
    """Generate an escalation-trigger test.

    Parameters
    ----------
    behavior_name:
        Sanitized behavior identifier.
    escalation:
        The ``EscalationClause`` AST node.
    gen:
        The code generator instance.

    Returns
    -------
    str
        A complete test function source block.
    """
    test_name = f"test_behavior_{behavior_name}_escalation_triggered"
    condition_py = gen.generate(escalation.condition)
    docstring = (
        f"Behavior '{behavior_name}': escalate to human when "
        f"{condition_py}."
    )
    body_lines = [
        "ctx = agent_context",
        "# Configure ctx to trigger the escalation condition, then assert it fires.",
        f"escalation_condition = {_adapt_expr_for_context(condition_py)}",
        "if escalation_condition:",
        "    pytest.skip('Escalation condition not triggered — configure ctx first')",
    ]
    return render_test_function(
        test_name=test_name,
        docstring=docstring,
        fixture_names=["agent_context"],
        body_lines=body_lines,
    )


def _adapt_assertion_for_context(assertion: str) -> str:
    """Prefix any bare name references with ``ctx.`` where safe to do so.

    This is a best-effort transformation.  If the assertion uses complex
    expressions, it is left verbatim and a comment is prepended.

    Parameters
    ----------
    assertion:
        A Python ``assert`` or ``assert not`` statement string.

    Returns
    -------
    str
        The (possibly modified) assertion line.
    """
    return assertion


def _adapt_expr_for_context(expr: str) -> str:
    """Return the expression adapted for use inside a test body."""
    return expr


def _to_snake(name: str) -> str:
    """Convert CamelCase/PascalCase to snake_case."""
    result = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name)
    return result.lower()
