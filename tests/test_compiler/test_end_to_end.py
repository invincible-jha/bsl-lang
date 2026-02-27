"""End-to-end tests: BSL source string → compile → valid pytest output.

These tests exercise the full pipeline:
  1. Parse a BSL source string to an AgentSpec AST (using bsl.parse).
  2. Compile with bsl.compiler.compile → CompilerOutput.
  3. Assert the generated source is syntactically valid Python.
  4. Assert expected test function names are present.

Tests do NOT execute the generated pytest files (that would create a
recursive test dependency).  Instead they verify the generated code can
be imported by Python's AST parser and contain the expected structure.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import bsl
from bsl.compiler import compile as bsl_compile, CompilerOutput


# ---------------------------------------------------------------------------
# Inline BSL sources (avoid file I/O in fast unit tests)
# ---------------------------------------------------------------------------

_BASIC_BSL = """\
agent BasicAgent {
  version: "1.0"
  model: "gpt-4o"
  owner: "test@example.com"

  behavior respond {
    must: response contains "Hello"
    must_not: response contains "error"
    confidence: >= 90%
    audit: basic
  }

  invariant no_pii {
    applies_to: all_behaviors
    severity: critical

    must_not: response contains "SSN"
    must_not: response contains "credit_card"
  }
}
"""

_MULTI_BEHAVIOR_BSL = """\
agent MultiAgent {
  version: "2.0"
  model: "gpt-4o"
  owner: "ops@example.com"

  behavior greet {
    must: response contains "Hello"
    must: response contains customer_name
    must_not: response contains "robot"
    should: response.tone == "warm" 90% of cases
  }

  behavior respond {
    when: request.type == "query"
    confidence: >= 85%
    latency: < 2000
    cost: < 0.05

    escalate_to_human when: query.sensitivity > 8

    must: response.length < 2000
    must: response contains answer
    must_not: response contains internal_data
  }

  invariant safety {
    applies_to: all_behaviors
    severity: critical

    must: response.toxicity_score < 0.1
    must_not: response contains hate_speech
  }
}
"""

_MINIMAL_BSL = """\
agent MinimalAgent {
  version: "0.1"
  behavior check {
    must: status == true
  }
}
"""

_THRESHOLD_HEAVY_BSL = """\
agent ThresholdAgent {
  version: "1.0"
  model: "gpt-4o"
  owner: "perf@example.com"

  behavior fast_respond {
    confidence: >= 95%
    latency: < 300
    cost: < 0.01
    audit: basic

    must: response.ready == true
  }
}
"""

_IN_LIST_BSL = """\
agent CategoryAgent {
  version: "1.0"

  behavior classify {
    must: response.category in ["A", "B", "C"]
    must_not: response.category == "unknown"
  }
}
"""


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _parse_and_compile(bsl_source: str) -> CompilerOutput:
    """Parse BSL source, compile, and return the CompilerOutput."""
    spec = bsl.parse(bsl_source)
    return bsl_compile(spec, target="pytest")


def _source(output: CompilerOutput) -> str:
    """Return the single generated Python source string."""
    assert len(output.files) == 1
    return list(output.files.values())[0]


def _test_names(output: CompilerOutput) -> set[str]:
    """Extract all test function names from the generated source."""
    source = _source(output)
    tree = ast.parse(source)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }


# ---------------------------------------------------------------------------
# Pipeline smoke tests
# ---------------------------------------------------------------------------


class TestPipelineSmoke:
    def test_basic_bsl_parses_and_compiles(self) -> None:
        output = _parse_and_compile(_BASIC_BSL)
        assert isinstance(output, CompilerOutput)

    def test_basic_bsl_generates_one_file(self) -> None:
        output = _parse_and_compile(_BASIC_BSL)
        assert len(output.files) == 1

    def test_multi_behavior_bsl_compiles(self) -> None:
        output = _parse_and_compile(_MULTI_BEHAVIOR_BSL)
        assert output.test_count > 0

    def test_minimal_bsl_compiles(self) -> None:
        output = _parse_and_compile(_MINIMAL_BSL)
        assert isinstance(output, CompilerOutput)

    def test_threshold_heavy_bsl_compiles(self) -> None:
        output = _parse_and_compile(_THRESHOLD_HEAVY_BSL)
        assert output.test_count > 0


# ---------------------------------------------------------------------------
# Syntax validity
# ---------------------------------------------------------------------------


class TestSyntaxValidity:
    def test_basic_bsl_output_is_valid_python(self) -> None:
        source = _source(_parse_and_compile(_BASIC_BSL))
        ast.parse(source)  # raises SyntaxError if invalid

    def test_multi_behavior_output_is_valid_python(self) -> None:
        source = _source(_parse_and_compile(_MULTI_BEHAVIOR_BSL))
        ast.parse(source)

    def test_minimal_output_is_valid_python(self) -> None:
        source = _source(_parse_and_compile(_MINIMAL_BSL))
        ast.parse(source)

    def test_threshold_output_is_valid_python(self) -> None:
        source = _source(_parse_and_compile(_THRESHOLD_HEAVY_BSL))
        ast.parse(source)

    def test_in_list_output_is_valid_python(self) -> None:
        source = _source(_parse_and_compile(_IN_LIST_BSL))
        ast.parse(source)


# ---------------------------------------------------------------------------
# Test function name correctness
# ---------------------------------------------------------------------------


class TestGeneratedTestNames:
    def test_basic_invariant_must_not_tests_present(self) -> None:
        names = _test_names(_parse_and_compile(_BASIC_BSL))
        must_not_tests = {n for n in names if "must_not" in n and "no_pii" in n}
        assert len(must_not_tests) >= 2  # two must_not constraints in no_pii

    def test_behavior_must_test_present(self) -> None:
        names = _test_names(_parse_and_compile(_BASIC_BSL))
        assert any("respond" in n and "must_0" in n for n in names)

    def test_behavior_must_not_test_present(self) -> None:
        names = _test_names(_parse_and_compile(_BASIC_BSL))
        assert any("respond" in n and "must_not_0" in n for n in names)

    def test_multi_behavior_names_include_both_behaviors(self) -> None:
        names = _test_names(_parse_and_compile(_MULTI_BEHAVIOR_BSL))
        greet_tests = {n for n in names if "greet" in n}
        respond_tests = {n for n in names if "respond" in n}
        assert len(greet_tests) > 0
        assert len(respond_tests) > 0

    def test_escalation_test_generated(self) -> None:
        names = _test_names(_parse_and_compile(_MULTI_BEHAVIOR_BSL))
        assert any("escalation" in n for n in names)

    def test_threshold_tests_generated(self) -> None:
        names = _test_names(_parse_and_compile(_THRESHOLD_HEAVY_BSL))
        assert any("confidence_threshold" in n for n in names)
        assert any("latency_threshold" in n for n in names)
        assert any("cost_threshold" in n for n in names)

    def test_should_tests_have_xfail_marker(self) -> None:
        source = _source(_parse_and_compile(_MULTI_BEHAVIOR_BSL))
        # The xfail marker should appear in the source for soft constraints.
        assert "xfail" in source

    def test_all_generated_names_start_with_test_prefix(self) -> None:
        names = _test_names(_parse_and_compile(_MULTI_BEHAVIOR_BSL))
        assert all(n.startswith("test_") for n in names)


# ---------------------------------------------------------------------------
# Test count correctness
# ---------------------------------------------------------------------------


class TestTestCountAccuracy:
    def test_basic_spec_test_count(self) -> None:
        # respond: must(1) + must_not(1) + confidence(1) = 3
        # no_pii: must_not(2) = 2
        # Total = 5
        output = _parse_and_compile(_BASIC_BSL)
        assert output.test_count == 5

    def test_minimal_spec_test_count(self) -> None:
        # check: must(1) = 1
        output = _parse_and_compile(_MINIMAL_BSL)
        assert output.test_count == 1

    def test_test_count_matches_function_count(self) -> None:
        output = _parse_and_compile(_MULTI_BEHAVIOR_BSL)
        names = _test_names(output)
        # agent_context fixture should not be counted
        non_fixture = {n for n in names if not n == "agent_context"}
        assert output.test_count == len(non_fixture)


# ---------------------------------------------------------------------------
# Metadata correctness
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_agent_name_in_metadata(self) -> None:
        output = _parse_and_compile(_BASIC_BSL)
        assert output.metadata["agent_name"] == "BasicAgent"

    def test_agent_version_in_metadata(self) -> None:
        output = _parse_and_compile(_BASIC_BSL)
        assert output.metadata["agent_version"] == "1.0"

    def test_invariant_count_in_metadata(self) -> None:
        output = _parse_and_compile(_BASIC_BSL)
        assert output.metadata["invariant_count"] == 1

    def test_behavior_count_in_metadata(self) -> None:
        output = _parse_and_compile(_BASIC_BSL)
        assert output.metadata["behavior_count"] == 1

    def test_generated_at_in_metadata(self) -> None:
        output = _parse_and_compile(_BASIC_BSL)
        assert "generated_at" in output.metadata


# ---------------------------------------------------------------------------
# Fixture file tests (reads .bsl files from tests/fixtures/sample_specs/)
# ---------------------------------------------------------------------------


def _fixture_dir() -> Path:
    """Return the path to tests/fixtures/sample_specs/."""
    return Path(__file__).parent.parent / "fixtures" / "sample_specs"


@pytest.mark.parametrize("bsl_filename", ["basic.bsl", "healthcare.bsl", "multi_rule.bsl"])
def test_fixture_file_compiles_to_valid_python(bsl_filename: str) -> None:
    """Each fixture BSL file should compile to syntactically valid Python."""
    fixture_path = _fixture_dir() / bsl_filename
    if not fixture_path.exists():
        pytest.skip(f"Fixture file not found: {fixture_path}")
    bsl_source = fixture_path.read_text(encoding="utf-8")
    output = _parse_and_compile(bsl_source)
    source = _source(output)
    ast.parse(source)  # raises SyntaxError if invalid


@pytest.mark.parametrize("bsl_filename", ["basic.bsl", "healthcare.bsl", "multi_rule.bsl"])
def test_fixture_file_generates_tests(bsl_filename: str) -> None:
    """Each fixture BSL file should produce at least one test function."""
    fixture_path = _fixture_dir() / bsl_filename
    if not fixture_path.exists():
        pytest.skip(f"Fixture file not found: {fixture_path}")
    bsl_source = fixture_path.read_text(encoding="utf-8")
    output = _parse_and_compile(bsl_source)
    assert output.test_count > 0


# ---------------------------------------------------------------------------
# Public API surface test
# ---------------------------------------------------------------------------


class TestPublicAPI:
    def test_bsl_compile_function_accepts_target_arg(self) -> None:
        spec = bsl.parse(_MINIMAL_BSL)
        output = bsl_compile(spec, target="pytest")
        assert isinstance(output, CompilerOutput)

    def test_bsl_compile_raises_for_unknown_target(self) -> None:
        spec = bsl.parse(_MINIMAL_BSL)
        with pytest.raises(ValueError, match="Unknown compiler target"):
            bsl_compile(spec, target="nonexistent_target")

    def test_available_targets_includes_pytest(self) -> None:
        from bsl.compiler import available_targets

        assert "pytest" in available_targets()

    def test_compiler_output_summary_method(self) -> None:
        output = _parse_and_compile(_BASIC_BSL)
        summary = output.summary()
        assert isinstance(summary, str)
        assert "test case" in summary.lower()
