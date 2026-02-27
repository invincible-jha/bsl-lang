"""NL -> BSL -> AST -> compiled output pipeline (compiler bridge).

Connects the existing NL translator, BSL parser, and optional compiler
into a single convenience pipeline.  All intermediate artifacts are
preserved in the result so callers can inspect each stage independently.

Usage
-----
::

    from bsl.translate.providers import MockLLMProvider
    from bsl.translate.nl_to_bsl import NLToBSLTranslator
    from bsl.parser.parser import parse
    from bsl.compiler.pytest_target import PytestTarget
    from bsl.nl.compiler_bridge import CompilerBridge

    translator = NLToBSLTranslator(provider=MockLLMProvider())
    bridge = CompilerBridge(translator=translator, parser=parse)
    result = bridge.translate_and_parse(
        "agent SafetyAgent { behavior respond { must never expose_credentials } }"
    )
    print(result.bsl_text)
    print(result.ast)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from bsl.ast.nodes import AgentSpec
    from bsl.compiler.base import CompilerOutput, CompilerTarget
    from bsl.translate.nl_to_bsl import NLToBSLTranslator


@dataclass(frozen=True)
class CompilerBridgeResult:
    """Immutable result of a full NL -> BSL -> AST -> compiled pipeline run.

    Parameters
    ----------
    natural_language:
        The original NL input text.
    bsl_text:
        The BSL representation produced by the translator.
    ast:
        The parsed AST, or ``None`` if parsing failed.
    compiled_output:
        The compiled output (e.g. pytest source), or ``None`` when no
        compiler was provided or compilation was not requested.
    errors:
        Tuple of error message strings collected across all pipeline stages.
    """

    natural_language: str
    bsl_text: str
    ast: AgentSpec | None
    compiled_output: str | None
    errors: tuple[str, ...]

    @property
    def has_errors(self) -> bool:
        """Return ``True`` when any pipeline stage produced an error."""
        return len(self.errors) > 0

    @property
    def succeeded(self) -> bool:
        """Return ``True`` when the pipeline completed without errors."""
        return not self.has_errors and self.ast is not None


class CompilerBridge:
    """Pipeline that chains NL translation, BSL parsing, and optional compilation.

    Parameters
    ----------
    translator:
        An :class:`~bsl.translate.nl_to_bsl.NLToBSLTranslator` instance.
    parser:
        A callable that accepts a BSL source string and returns an
        ``AgentSpec``.  Defaults to :func:`~bsl.parser.parser.parse`.
    compiler:
        Optional :class:`~bsl.compiler.base.CompilerTarget` instance.
        When provided, :meth:`translate_parse_compile` will also invoke
        ``compiler.compile(ast)`` and include the first generated file
        in the result.
    """

    def __init__(
        self,
        translator: NLToBSLTranslator,
        parser: Callable[[str], AgentSpec] | None = None,
        compiler: CompilerTarget | None = None,
    ) -> None:
        self._translator = translator
        if parser is None:
            from bsl.parser.parser import parse as _default_parse

            parser = _default_parse
        self._parser: Callable[[str], AgentSpec] = parser
        self._compiler: CompilerTarget | None = compiler

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def translate_and_parse(self, nl_text: str) -> CompilerBridgeResult:
        """Translate NL to BSL then parse to AST.

        Stops after parsing — does not invoke the compiler even if one
        was provided.

        Parameters
        ----------
        nl_text:
            Natural-language text describing agent behavior, OR a raw
            BSL source string.  When the text looks like BSL (starts with
            the ``agent`` keyword) the translation step is skipped.

        Returns
        -------
        CompilerBridgeResult
            Result with ``bsl_text`` and ``ast`` populated.  ``compiled_output``
            is always ``None``.
        """
        bsl_text, translation_errors = self._translate(nl_text)
        ast_node, parse_errors = self._parse(bsl_text)
        all_errors = translation_errors + parse_errors
        return CompilerBridgeResult(
            natural_language=nl_text,
            bsl_text=bsl_text,
            ast=ast_node,
            compiled_output=None,
            errors=tuple(all_errors),
        )

    def translate_parse_compile(self, nl_text: str) -> CompilerBridgeResult:
        """Run the full NL -> BSL -> AST -> compiled output pipeline.

        Parameters
        ----------
        nl_text:
            Natural-language text or raw BSL source.

        Returns
        -------
        CompilerBridgeResult
            Result with all fields populated.  If no compiler was provided,
            ``compiled_output`` is ``None`` and a warning is added to ``errors``.
        """
        bsl_text, translation_errors = self._translate(nl_text)
        ast_node, parse_errors = self._parse(bsl_text)
        compiled_output: str | None = None
        compile_errors: list[str] = []

        if ast_node is not None:
            if self._compiler is None:
                compile_errors.append(
                    "No compiler provided to CompilerBridge; skipping compilation."
                )
            else:
                compiled_output, compile_errors = self._compile(ast_node)

        all_errors = translation_errors + parse_errors + compile_errors
        return CompilerBridgeResult(
            natural_language=nl_text,
            bsl_text=bsl_text,
            ast=ast_node,
            compiled_output=compiled_output,
            errors=tuple(all_errors),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _translate(self, nl_text: str) -> tuple[str, list[str]]:
        """Invoke the NL translator; return (bsl_text, errors)."""
        stripped = nl_text.strip()
        # If the input already looks like BSL, skip NL translation.
        if stripped.lower().startswith("agent "):
            return stripped, []
        try:
            bsl_text = self._translator.translate(stripped)
            return bsl_text, []
        except Exception as exc:  # noqa: BLE001
            error_msg = f"Translation failed: {exc}"
            return stripped, [error_msg]

    def _parse(self, bsl_text: str) -> tuple[AgentSpec | None, list[str]]:
        """Invoke the parser; return (ast_node, errors)."""
        try:
            ast_node = self._parser(bsl_text)
            return ast_node, []
        except Exception as exc:  # noqa: BLE001
            error_msg = f"Parse failed: {exc}"
            return None, [error_msg]

    def _compile(self, ast_node: AgentSpec) -> tuple[str | None, list[str]]:
        """Invoke the compiler; return (first_file_content, errors)."""
        assert self._compiler is not None
        try:
            compiler_output: CompilerOutput = self._compiler.compile(ast_node)
            # Return the first generated file content.
            first_file = next(iter(compiler_output.files.values()), None)
            compile_errors: list[str] = list(compiler_output.warnings)
            return first_file, compile_errors
        except Exception as exc:  # noqa: BLE001
            error_msg = f"Compilation failed: {exc}"
            return None, [error_msg]


__all__ = [
    "CompilerBridge",
    "CompilerBridgeResult",
]
