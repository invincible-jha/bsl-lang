"""BSL Compliance Test Generator.

Reads BSL invariants and behavior constraints from an ``AgentSpec`` and
generates pytest test stubs.  Each invariant and each constraint becomes
an independent, runnable test function that can be filled in with
project-specific assertion logic.

Usage
-----
::

    from bsl.testgen import ComplianceTestGenerator, TestGenConfig

    spec = parse("my_agent.bsl")
    config = TestGenConfig(include_behaviors=True, include_invariants=True)
    generator = ComplianceTestGenerator(config)
    result = generator.generate(spec)
    print(result.render())          # Full pytest file as string
    result.write("tests/test_compliance.py")
"""
from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from bsl.ast.nodes import (
    AgentSpec,
    AuditLevel,
    Behavior,
    BinOp,
    BinaryOpExpr,
    BoolLit,
    Constraint,
    ContainsExpr,
    DotAccess,
    EscalationClause,
    Expression,
    FunctionCall,
    Identifier,
    InListExpr,
    Invariant,
    NumberLit,
    ShouldConstraint,
    Severity,
    StringLit,
    ThresholdClause,
    UnaryOpExpr,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sanitize(name: str) -> str:
    """Convert a BSL name to a valid Python identifier fragment."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned.lower() if cleaned else "unnamed"


def _expr_to_comment(expr: Expression | None) -> str:
    """Render an expression to a short human-readable comment."""
    if expr is None:
        return "<none>"
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
        left = _expr_to_comment(expr.left)
        right = _expr_to_comment(expr.right)
        return f"{left} {expr.op.name.lower()} {right}"
    if isinstance(expr, UnaryOpExpr):
        return f"not {_expr_to_comment(expr.operand)}"
    if isinstance(expr, ContainsExpr):
        return f"{_expr_to_comment(expr.subject)} contains {_expr_to_comment(expr.value)}"
    if isinstance(expr, InListExpr):
        items = ", ".join(_expr_to_comment(i) for i in expr.items)
        return f"{_expr_to_comment(expr.subject)} in [{items}]"
    if isinstance(expr, FunctionCall):
        args = ", ".join(_expr_to_comment(a) for a in expr.arguments)
        return f"{expr.name}({args})"
    return repr(expr)


def _threshold_to_comment(t: ThresholdClause | None, field_name: str) -> str:
    if t is None:
        return f"no {field_name} threshold"
    pct = "%" if t.is_percentage else ""
    return f"{field_name} {t.operator} {t.value}{pct}"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GeneratedTest:
    """A single generated pytest test function.

    Parameters
    ----------
    function_name:
        The name of the generated test function.
    source:
        The body of the test function (indented Python code).
    origin_kind:
        ``"invariant"``, ``"behavior_must"``, ``"behavior_must_not"``,
        ``"behavior_should"``, ``"behavior_may"``, ``"behavior_threshold"``,
        ``"behavior_escalation"``, or ``"behavior_audit"``.
    origin_name:
        The BSL element name (behavior or invariant).
    description:
        Short human-readable description of what this test checks.
    skip_reason:
        Non-empty string if the generated test will ``pytest.skip`` because
        the constraint cannot be auto-verified.
    """

    function_name: str
    source: str
    origin_kind: str
    origin_name: str
    description: str
    skip_reason: str = ""


@dataclass
class TestGenConfig:
    """Configuration for :class:`ComplianceTestGenerator`.

    Parameters
    ----------
    include_invariants:
        Generate tests for invariant constraints (default True).
    include_behaviors:
        Generate tests for behavior constraints (default True).
    include_thresholds:
        Generate threshold assertion stubs (default True).
    include_escalation:
        Generate escalation clause tests (default True).
    include_audit:
        Generate audit-level tests (default False).
    fixture_name:
        Name of the pytest fixture injected into every test.
    agent_module_path:
        Optional import path for the agent under test (used in comments).
    """

    include_invariants: bool = True
    include_behaviors: bool = True
    include_thresholds: bool = True
    include_escalation: bool = True
    include_audit: bool = False
    fixture_name: str = "agent_context"
    agent_module_path: str = "your_agent_module"


@dataclass
class TestGenResult:
    """The full output of a :class:`ComplianceTestGenerator` run.

    Parameters
    ----------
    agent_name:
        Name of the agent spec that was processed.
    tests:
        All generated test objects, in generation order.
    config:
        The configuration used for this run.
    generated_at:
        ISO-8601 timestamp of when generation occurred.
    """

    agent_name: str
    tests: list[GeneratedTest] = field(default_factory=list)
    config: TestGenConfig = field(default_factory=TestGenConfig)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def test_count(self) -> int:
        """Total number of generated test functions."""
        return len(self.tests)

    @property
    def skipped_count(self) -> int:
        """Number of tests that will be skipped at runtime."""
        return sum(1 for t in self.tests if t.skip_reason)

    def by_kind(self, origin_kind: str) -> list[GeneratedTest]:
        """Return all tests with a given ``origin_kind``."""
        return [t for t in self.tests if t.origin_kind == origin_kind]

    def render(self) -> str:
        """Render all generated tests to a complete pytest file string.

        Returns
        -------
        str
            A valid Python source file containing all test functions,
            a module docstring, and a shared fixture.
        """
        lines: list[str] = []

        # File header
        lines.append(
            f'"""Auto-generated compliance tests for agent: {self.agent_name}.\n'
            f"\n"
            f"Generated at: {self.generated_at}\n"
            f"BSL agent: {self.agent_name}\n"
            f"Test count: {self.test_count}\n"
            f"\n"
            f"DO NOT EDIT MANUALLY — regenerate from the BSL spec.\n"
            f'"""'
        )
        lines.append("from __future__ import annotations")
        lines.append("")
        lines.append("import pytest")
        lines.append("")

        # Shared fixture
        fixture_name = self.config.fixture_name
        lines.append("")
        lines.append(f"@pytest.fixture()")
        lines.append(f"def {fixture_name}():")
        lines.append(
            f'    """Minimal agent context for compliance tests."""'
        )
        lines.append(f"    return {{")
        lines.append(f'        "agent_name": {self.agent_name!r},')
        lines.append(f'        "module": "{self.config.agent_module_path}",')
        lines.append(f"    }}")
        lines.append("")
        lines.append("")

        # Group tests by origin kind
        if not self.tests:
            lines.append("# No tests generated — spec has no invariants or constraints.")
            return "\n".join(lines)

        current_section: str | None = None
        for test in self.tests:
            section = test.origin_kind
            if section != current_section:
                lines.append(f"# {'=' * 70}")
                lines.append(f"# Section: {section.replace('_', ' ').title()}")
                lines.append(f"# {'=' * 70}")
                lines.append("")
                current_section = section
            lines.append(test.source)
            lines.append("")

        return "\n".join(lines)

    def write(self, output_path: str | Path) -> Path:
        """Write the rendered test file to disk.

        Parameters
        ----------
        output_path:
            Path to the output ``.py`` file. Parent directories are
            created automatically.

        Returns
        -------
        Path
            The resolved path where the file was written.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(), encoding="utf-8")
        return path


# ---------------------------------------------------------------------------
# ComplianceTestGenerator
# ---------------------------------------------------------------------------


class ComplianceTestGenerator:
    """Generate pytest compliance test stubs from a BSL ``AgentSpec``.

    Each BSL invariant constraint becomes a ``test_invariant_*`` function.
    Each behavior constraint becomes a ``test_behavior_*`` function.
    Threshold clauses become assertion stubs with TODO comments.
    Escalation clauses produce tests that verify escalation logic.

    Parameters
    ----------
    config:
        Controls which elements are included in the generated output.
        Defaults to :class:`TestGenConfig` with all elements enabled.

    Example
    -------
    ::

        from bsl.testgen import ComplianceTestGenerator
        from bsl.convenience import parse

        spec = parse(source)
        result = ComplianceTestGenerator().generate(spec)
        result.write("tests/test_compliance.py")
    """

    def __init__(self, config: TestGenConfig | None = None) -> None:
        self._config = config or TestGenConfig()
        self._seen_names: set[str] = set()

    def generate(self, spec: AgentSpec) -> TestGenResult:
        """Generate compliance tests for all elements in *spec*.

        Parameters
        ----------
        spec:
            A parsed BSL agent specification.

        Returns
        -------
        TestGenResult
            The structured result containing all generated tests.
        """
        self._seen_names = set()
        result = TestGenResult(agent_name=spec.name, config=self._config)

        if self._config.include_invariants:
            for invariant in spec.invariants:
                result.tests.extend(self._gen_invariant_tests(invariant))

        if self._config.include_behaviors:
            for behavior in spec.behaviors:
                result.tests.extend(self._gen_behavior_tests(behavior))

        return result

    # ------------------------------------------------------------------
    # Invariant generators
    # ------------------------------------------------------------------

    def _gen_invariant_tests(self, invariant: Invariant) -> list[GeneratedTest]:
        tests: list[GeneratedTest] = []
        inv_name = _sanitize(invariant.name)
        severity_label = invariant.severity.name.lower()

        for index, constraint in enumerate(invariant.constraints):
            expr_comment = _expr_to_comment(constraint.expression)
            func_name = self._unique_name(
                f"test_invariant_{inv_name}_must_{index}"
            )
            description = (
                f"Invariant '{invariant.name}' constraint #{index}: must {expr_comment}"
            )
            source = self._render_test(
                func_name=func_name,
                fixture_name=self._config.fixture_name,
                docstring=(
                    f"Invariant '{invariant.name}' (severity={severity_label.upper()}): "
                    f"must hold: {expr_comment}"
                ),
                body_lines=[
                    f"# BSL invariant: {invariant.name}",
                    f"# Constraint: must {expr_comment}",
                    f"# Severity: {severity_label.upper()}",
                    f"# TODO: implement assertion that verifies this invariant holds.",
                    f"assert True  # Replace with real assertion.",
                ],
                skip_reason="",
            )
            tests.append(
                GeneratedTest(
                    function_name=func_name,
                    source=source,
                    origin_kind="invariant",
                    origin_name=invariant.name,
                    description=description,
                )
            )

        for index, prohibition in enumerate(invariant.prohibitions):
            expr_comment = _expr_to_comment(prohibition.expression)
            func_name = self._unique_name(
                f"test_invariant_{inv_name}_must_not_{index}"
            )
            description = (
                f"Invariant '{invariant.name}' prohibition #{index}: must not {expr_comment}"
            )
            source = self._render_test(
                func_name=func_name,
                fixture_name=self._config.fixture_name,
                docstring=(
                    f"Invariant '{invariant.name}' (severity={severity_label.upper()}): "
                    f"must NOT hold: {expr_comment}"
                ),
                body_lines=[
                    f"# BSL invariant: {invariant.name}",
                    f"# Prohibition: must NOT {expr_comment}",
                    f"# Severity: {severity_label.upper()}",
                    f"# TODO: implement assertion that verifies this prohibition is never violated.",
                    f"assert True  # Replace with real assertion.",
                ],
                skip_reason="",
            )
            tests.append(
                GeneratedTest(
                    function_name=func_name,
                    source=source,
                    origin_kind="invariant",
                    origin_name=invariant.name,
                    description=description,
                )
            )

        return tests

    # ------------------------------------------------------------------
    # Behavior generators
    # ------------------------------------------------------------------

    def _gen_behavior_tests(self, behavior: Behavior) -> list[GeneratedTest]:
        tests: list[GeneratedTest] = []
        beh_name = _sanitize(behavior.name)

        # must constraints
        for index, constraint in enumerate(behavior.must_constraints):
            tests.append(
                self._gen_constraint_test(
                    behavior_name=behavior.name,
                    beh_safe=beh_name,
                    constraint=constraint,
                    constraint_type="must",
                    index=index,
                    origin_kind="behavior_must",
                )
            )

        # must_not constraints
        for index, constraint in enumerate(behavior.must_not_constraints):
            tests.append(
                self._gen_constraint_test(
                    behavior_name=behavior.name,
                    beh_safe=beh_name,
                    constraint=constraint,
                    constraint_type="must_not",
                    index=index,
                    origin_kind="behavior_must_not",
                )
            )

        # should constraints
        for index, should in enumerate(behavior.should_constraints):
            tests.append(
                self._gen_should_test(
                    behavior_name=behavior.name,
                    beh_safe=beh_name,
                    should=should,
                    index=index,
                )
            )

        # may constraints (just document, no enforcement)
        for index, constraint in enumerate(behavior.may_constraints):
            tests.append(
                self._gen_constraint_test(
                    behavior_name=behavior.name,
                    beh_safe=beh_name,
                    constraint=constraint,
                    constraint_type="may",
                    index=index,
                    origin_kind="behavior_may",
                )
            )

        if self._config.include_thresholds:
            # confidence
            if behavior.confidence is not None:
                tests.append(
                    self._gen_threshold_test(behavior, "confidence", behavior.confidence)
                )
            # latency
            if behavior.latency is not None:
                tests.append(
                    self._gen_threshold_test(behavior, "latency", behavior.latency)
                )
            # cost
            if behavior.cost is not None:
                tests.append(
                    self._gen_threshold_test(behavior, "cost", behavior.cost)
                )

        if self._config.include_escalation and behavior.escalation is not None:
            tests.append(self._gen_escalation_test(behavior))

        if self._config.include_audit and behavior.audit != AuditLevel.NONE:
            tests.append(self._gen_audit_test(behavior))

        return tests

    def _gen_constraint_test(
        self,
        behavior_name: str,
        beh_safe: str,
        constraint: Constraint,
        constraint_type: str,
        index: int,
        origin_kind: str,
    ) -> GeneratedTest:
        expr_comment = _expr_to_comment(constraint.expression)
        func_name = self._unique_name(
            f"test_behavior_{beh_safe}_{constraint_type}_{index}"
        )
        verb = "must NOT" if constraint_type == "must_not" else constraint_type.upper()
        docstring = (
            f"Behavior '{behavior_name}' — {verb}: {expr_comment}"
        )
        body_lines = [
            f"# Behavior: {behavior_name}",
            f"# Constraint ({constraint_type}): {expr_comment}",
            f"# TODO: call agent and assert this constraint holds.",
            f"assert True  # Replace with real assertion.",
        ]
        return GeneratedTest(
            function_name=func_name,
            source=self._render_test(
                func_name=func_name,
                fixture_name=self._config.fixture_name,
                docstring=docstring,
                body_lines=body_lines,
                skip_reason="",
            ),
            origin_kind=origin_kind,
            origin_name=behavior_name,
            description=docstring,
        )

    def _gen_should_test(
        self,
        behavior_name: str,
        beh_safe: str,
        should: ShouldConstraint,
        index: int,
    ) -> GeneratedTest:
        expr_comment = _expr_to_comment(should.expression)
        pct_note = f" (in at least {should.percentage}% of cases)" if should.percentage is not None else ""
        func_name = self._unique_name(f"test_behavior_{beh_safe}_should_{index}")
        docstring = (
            f"Behavior '{behavior_name}' — SHOULD{pct_note}: {expr_comment}"
        )
        body_lines = [
            f"# Behavior: {behavior_name}",
            f"# Should constraint{pct_note}: {expr_comment}",
            f"# TODO: verify this soft constraint over a sample of agent calls.",
            "pytest.skip('SHOULD constraint — verify via statistical sampling.')",
        ]
        return GeneratedTest(
            function_name=func_name,
            source=self._render_test(
                func_name=func_name,
                fixture_name=self._config.fixture_name,
                docstring=docstring,
                body_lines=body_lines,
                skip_reason="SHOULD constraint — verify via statistical sampling.",
            ),
            origin_kind="behavior_should",
            origin_name=behavior_name,
            description=docstring,
            skip_reason="SHOULD constraint — verify via statistical sampling.",
        )

    def _gen_threshold_test(
        self, behavior: Behavior, field_name: str, threshold: ThresholdClause
    ) -> GeneratedTest:
        beh_safe = _sanitize(behavior.name)
        func_name = self._unique_name(
            f"test_behavior_{beh_safe}_{field_name}_threshold"
        )
        pct = "%" if threshold.is_percentage else ""
        constraint_text = f"{field_name} {threshold.operator} {threshold.value}{pct}"
        docstring = f"Behavior '{behavior.name}' — threshold: {constraint_text}"
        body_lines = [
            f"# Behavior: {behavior.name}",
            f"# Threshold: {constraint_text}",
            f"# TODO: measure {field_name} over representative workload.",
            f"assert True  # Replace with real {field_name} measurement.",
        ]
        return GeneratedTest(
            function_name=func_name,
            source=self._render_test(
                func_name=func_name,
                fixture_name=self._config.fixture_name,
                docstring=docstring,
                body_lines=body_lines,
                skip_reason="",
            ),
            origin_kind="behavior_threshold",
            origin_name=behavior.name,
            description=docstring,
        )

    def _gen_escalation_test(self, behavior: Behavior) -> GeneratedTest:
        beh_safe = _sanitize(behavior.name)
        func_name = self._unique_name(f"test_behavior_{beh_safe}_escalation")
        assert behavior.escalation is not None
        cond = _expr_to_comment(behavior.escalation.condition)
        docstring = f"Behavior '{behavior.name}' — escalation triggers when: {cond}"
        body_lines = [
            f"# Behavior: {behavior.name}",
            f"# Escalation condition: {cond}",
            f"# TODO: verify agent escalates to human when condition holds.",
            f"assert True  # Replace with real escalation assertion.",
        ]
        return GeneratedTest(
            function_name=func_name,
            source=self._render_test(
                func_name=func_name,
                fixture_name=self._config.fixture_name,
                docstring=docstring,
                body_lines=body_lines,
                skip_reason="",
            ),
            origin_kind="behavior_escalation",
            origin_name=behavior.name,
            description=docstring,
        )

    def _gen_audit_test(self, behavior: Behavior) -> GeneratedTest:
        beh_safe = _sanitize(behavior.name)
        func_name = self._unique_name(f"test_behavior_{beh_safe}_audit")
        level = behavior.audit.name
        docstring = (
            f"Behavior '{behavior.name}' — audit level must be: {level}"
        )
        body_lines = [
            f"# Behavior: {behavior.name}",
            f"# Required audit level: {level}",
            f"# TODO: verify audit logs are produced at {level} detail.",
            f"assert True  # Replace with real audit log assertion.",
        ]
        return GeneratedTest(
            function_name=func_name,
            source=self._render_test(
                func_name=func_name,
                fixture_name=self._config.fixture_name,
                docstring=docstring,
                body_lines=body_lines,
                skip_reason="",
            ),
            origin_kind="behavior_audit",
            origin_name=behavior.name,
            description=docstring,
        )

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render_test(
        self,
        func_name: str,
        fixture_name: str,
        docstring: str,
        body_lines: list[str],
        skip_reason: str,
    ) -> str:
        """Render a single test function as a Python source string."""
        lines: list[str] = []
        lines.append(f"def {func_name}({fixture_name}):")
        lines.append(f'    """{docstring}"""')
        for body_line in body_lines:
            lines.append(f"    {body_line}")
        return "\n".join(lines)

    def _unique_name(self, candidate: str) -> str:
        """Return *candidate* ensuring uniqueness by appending a numeric suffix."""
        if candidate not in self._seen_names:
            self._seen_names.add(candidate)
            return candidate
        counter = 2
        while True:
            numbered = f"{candidate}_{counter}"
            if numbered not in self._seen_names:
                self._seen_names.add(numbered)
                return numbered
            counter += 1
