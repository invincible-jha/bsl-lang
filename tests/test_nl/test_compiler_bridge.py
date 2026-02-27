"""Tests for bsl.nl.compiler_bridge — NL -> BSL -> AST -> compiled pipeline."""
from __future__ import annotations

import pytest

from bsl.ast.nodes import AgentSpec
from bsl.compiler.pytest_target import PytestTarget
from bsl.nl.compiler_bridge import CompilerBridge, CompilerBridgeResult
from bsl.parser.parser import parse
from bsl.translate.nl_to_bsl import NLToBSLTranslator
from bsl.translate.providers import MockLLMProvider, TemplateProvider

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SIMPLE_BSL = """\
agent TestAgent {
    version: "1.0"
    behavior respond {
        must: response
        must_not: error
    }
    invariant safety {
        must_not: expose_pii
    }
}
"""

_MULTI_BEHAVIOR_BSL = """\
agent MultiAgent {
    behavior search {
        must: query
        must_not: leak
        confidence: >= 90%
    }
    behavior respond {
        should: format_output
    }
}
"""


@pytest.fixture()
def mock_translator() -> NLToBSLTranslator:
    """Return a translator backed by the deterministic mock provider."""
    return NLToBSLTranslator(provider=MockLLMProvider())


@pytest.fixture()
def template_translator() -> NLToBSLTranslator:
    """Return a translator backed by the template provider."""
    return NLToBSLTranslator(provider=TemplateProvider())


@pytest.fixture()
def pytest_compiler() -> PytestTarget:
    """Return a PytestTarget compiler instance."""
    return PytestTarget()


@pytest.fixture()
def bridge_no_compiler(mock_translator: NLToBSLTranslator) -> CompilerBridge:
    """Return a CompilerBridge without a compiler attached."""
    return CompilerBridge(translator=mock_translator, parser=parse)


@pytest.fixture()
def bridge_with_compiler(
    mock_translator: NLToBSLTranslator,
    pytest_compiler: PytestTarget,
) -> CompilerBridge:
    """Return a CompilerBridge with PytestTarget compiler attached."""
    return CompilerBridge(
        translator=mock_translator,
        parser=parse,
        compiler=pytest_compiler,
    )


# ---------------------------------------------------------------------------
# CompilerBridgeResult unit tests
# ---------------------------------------------------------------------------


class TestCompilerBridgeResult:
    def test_has_errors_false_when_no_errors(self) -> None:
        result = CompilerBridgeResult(
            natural_language="test",
            bsl_text="REQUIRE: test",
            ast=None,
            compiled_output=None,
            errors=(),
        )
        assert result.has_errors is False

    def test_has_errors_true_when_errors_present(self) -> None:
        result = CompilerBridgeResult(
            natural_language="test",
            bsl_text="",
            ast=None,
            compiled_output=None,
            errors=("Translation failed",),
        )
        assert result.has_errors is True

    def test_succeeded_requires_ast_and_no_errors(self) -> None:
        mock_ast = parse(_SIMPLE_BSL)
        result = CompilerBridgeResult(
            natural_language="test",
            bsl_text=_SIMPLE_BSL,
            ast=mock_ast,
            compiled_output=None,
            errors=(),
        )
        assert result.succeeded is True

    def test_succeeded_false_when_ast_is_none(self) -> None:
        result = CompilerBridgeResult(
            natural_language="test",
            bsl_text="",
            ast=None,
            compiled_output=None,
            errors=(),
        )
        assert result.succeeded is False

    def test_succeeded_false_when_errors_present(self) -> None:
        mock_ast = parse(_SIMPLE_BSL)
        result = CompilerBridgeResult(
            natural_language="test",
            bsl_text=_SIMPLE_BSL,
            ast=mock_ast,
            compiled_output=None,
            errors=("some warning",),
        )
        assert result.succeeded is False

    def test_frozen_dataclass_immutable(self) -> None:
        result = CompilerBridgeResult(
            natural_language="test",
            bsl_text="x",
            ast=None,
            compiled_output=None,
            errors=(),
        )
        with pytest.raises((AttributeError, TypeError)):
            result.natural_language = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CompilerBridge.translate_and_parse — BSL passthrough
# ---------------------------------------------------------------------------


class TestTranslateAndParseBSLPassthrough:
    """When input already looks like BSL, translation is skipped."""

    def test_bsl_input_sets_bsl_text_correctly(self, bridge_no_compiler: CompilerBridge) -> None:
        result = bridge_no_compiler.translate_and_parse(_SIMPLE_BSL)
        assert result.bsl_text.strip() == _SIMPLE_BSL.strip()

    def test_bsl_input_natural_language_preserved(self, bridge_no_compiler: CompilerBridge) -> None:
        result = bridge_no_compiler.translate_and_parse(_SIMPLE_BSL)
        assert result.natural_language == _SIMPLE_BSL

    def test_bsl_input_produces_ast(self, bridge_no_compiler: CompilerBridge) -> None:
        result = bridge_no_compiler.translate_and_parse(_SIMPLE_BSL)
        assert result.ast is not None
        assert isinstance(result.ast, AgentSpec)

    def test_bsl_input_ast_has_correct_name(self, bridge_no_compiler: CompilerBridge) -> None:
        result = bridge_no_compiler.translate_and_parse(_SIMPLE_BSL)
        assert result.ast is not None
        assert result.ast.name == "TestAgent"

    def test_bsl_input_no_errors(self, bridge_no_compiler: CompilerBridge) -> None:
        result = bridge_no_compiler.translate_and_parse(_SIMPLE_BSL)
        assert result.errors == ()

    def test_bsl_input_compiled_output_none(self, bridge_no_compiler: CompilerBridge) -> None:
        result = bridge_no_compiler.translate_and_parse(_SIMPLE_BSL)
        assert result.compiled_output is None


# ---------------------------------------------------------------------------
# CompilerBridge.translate_and_parse — NL translation path
# ---------------------------------------------------------------------------


class TestTranslateAndParseNLPath:
    """NL input is translated through MockLLMProvider before parsing."""

    def test_nl_input_must_never_produces_forbid(self, bridge_no_compiler: CompilerBridge) -> None:
        result = bridge_no_compiler.translate_and_parse("must never expose credentials")
        assert result.bsl_text.startswith("FORBID:")

    def test_nl_input_translation_error_captured(self) -> None:
        class FailProvider:
            def translate(self, text: str) -> str:
                raise RuntimeError("provider down")

        translator = NLToBSLTranslator(provider=FailProvider())
        bridge = CompilerBridge(translator=translator, parser=parse)
        result = bridge.translate_and_parse("must never fail")
        assert result.has_errors is True
        assert any("Translation failed" in e for e in result.errors)

    def test_parse_error_captured(self, bridge_no_compiler: CompilerBridge) -> None:
        # Malformed BSL that starts with 'agent' to bypass NL translation
        malformed = "agent { broken syntax }"
        result = bridge_no_compiler.translate_and_parse(malformed)
        assert result.has_errors is True


# ---------------------------------------------------------------------------
# CompilerBridge.translate_parse_compile — with compiler
# ---------------------------------------------------------------------------


class TestTranslateParseCompile:
    def test_compile_produces_output(self, bridge_with_compiler: CompilerBridge) -> None:
        result = bridge_with_compiler.translate_parse_compile(_SIMPLE_BSL)
        assert result.compiled_output is not None

    def test_compile_output_contains_import_pytest(self, bridge_with_compiler: CompilerBridge) -> None:
        result = bridge_with_compiler.translate_parse_compile(_SIMPLE_BSL)
        assert result.compiled_output is not None
        assert "import pytest" in result.compiled_output

    def test_compile_output_has_test_functions(self, bridge_with_compiler: CompilerBridge) -> None:
        result = bridge_with_compiler.translate_parse_compile(_SIMPLE_BSL)
        assert result.compiled_output is not None
        assert "def test_" in result.compiled_output

    def test_compile_no_errors_on_valid_bsl(self, bridge_with_compiler: CompilerBridge) -> None:
        result = bridge_with_compiler.translate_parse_compile(_SIMPLE_BSL)
        assert not result.has_errors

    def test_compile_without_compiler_gives_warning(self, bridge_no_compiler: CompilerBridge) -> None:
        result = bridge_no_compiler.translate_parse_compile(_SIMPLE_BSL)
        assert result.compiled_output is None
        assert any("compiler" in e.lower() for e in result.errors)

    def test_compile_with_multi_behavior_bsl(self, bridge_with_compiler: CompilerBridge) -> None:
        result = bridge_with_compiler.translate_parse_compile(_MULTI_BEHAVIOR_BSL)
        assert result.ast is not None
        assert result.compiled_output is not None
        assert result.ast.name == "MultiAgent"

    def test_compile_result_preserves_nl_input(self, bridge_with_compiler: CompilerBridge) -> None:
        result = bridge_with_compiler.translate_parse_compile(_SIMPLE_BSL)
        assert result.natural_language == _SIMPLE_BSL


# ---------------------------------------------------------------------------
# CompilerBridge constructor — default parser injection
# ---------------------------------------------------------------------------


class TestCompilerBridgeConstruction:
    def test_default_parser_is_injected(self, mock_translator: NLToBSLTranslator) -> None:
        bridge = CompilerBridge(translator=mock_translator)
        # Should not raise — uses default parse from bsl.parser.parser
        result = bridge.translate_and_parse(_SIMPLE_BSL)
        assert result.ast is not None

    def test_custom_parser_callable_accepted(self, mock_translator: NLToBSLTranslator) -> None:
        call_log: list[str] = []

        def recording_parser(source: str) -> AgentSpec:
            call_log.append(source)
            return parse(source)

        bridge = CompilerBridge(translator=mock_translator, parser=recording_parser)
        bridge.translate_and_parse(_SIMPLE_BSL)
        assert len(call_log) == 1
