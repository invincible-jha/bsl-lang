"""Abstract base class for BSL compilation targets.

Each compilation target (e.g. pytest, hypothesis) implements
``CompilerTarget`` and produces a ``CompilerOutput`` with one or more
generated source files.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bsl.ast.nodes import AgentSpec


@dataclass
class CompilerOutput:
    """Result of compiling a BSL agent specification.

    Parameters
    ----------
    files:
        Mapping of *relative* filename to generated Python source text.
        Callers decide where to write these files on disk.
    metadata:
        Arbitrary key/value pairs emitted by the compiler.  May include
        the agent name, BSL version, compilation timestamp, etc.
    test_count:
        Total number of test functions generated across all files.
    warnings:
        Non-fatal messages produced during compilation.  The caller
        should surface these to the user.
    """

    files: dict[str, str]
    metadata: dict[str, object] = field(default_factory=dict)
    test_count: int = 0
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Return a one-line human-readable summary of this output."""
        file_count = len(self.files)
        return (
            f"Generated {self.test_count} test case(s) "
            f"across {file_count} file(s)"
        )


class CompilerTarget(ABC):
    """Abstract base class for BSL-to-code compilation targets.

    Subclasses must implement :meth:`name` and :meth:`compile`.

    The contract for :meth:`compile` is:

    * **Idempotent** — identical inputs always produce identical outputs.
    * **Pure** — no side effects (no file I/O, no network calls).
    * **Total** — returns a ``CompilerOutput`` for any valid ``AgentSpec``.
      Emit warnings rather than raising exceptions for edge-cases.

    Parameters
    ----------
    indent_spaces:
        Number of spaces to use for indentation in generated code.
        Defaults to 4 (PEP 8).
    """

    def __init__(self, indent_spaces: int = 4) -> None:
        self._indent_spaces = indent_spaces

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique short name for this target, e.g. ``"pytest"``."""

    @abstractmethod
    def compile(self, spec: "AgentSpec") -> CompilerOutput:
        """Compile an ``AgentSpec`` to ``CompilerOutput``.

        Parameters
        ----------
        spec:
            The parsed agent specification to compile.

        Returns
        -------
        CompilerOutput
            The generated files and metadata.
        """

    def _indent(self, text: str, level: int = 1) -> str:
        """Indent *text* by ``level`` indentation units.

        Each unit is ``self._indent_spaces`` spaces.  Blank lines are
        left empty (no trailing whitespace).
        """
        prefix = " " * (self._indent_spaces * level)
        lines = text.splitlines()
        indented_lines = [
            prefix + line if line.strip() else ""
            for line in lines
        ]
        return "\n".join(indented_lines)
