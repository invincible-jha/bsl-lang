"""BSL compiler — transforms parsed ASTs into executable test code.

Public API
----------
The stable surface is the ``compile`` function and the ``CompilerOutput``
dataclass.  Everything else inside the compiler subpackage is private.

Example
-------
::

    import bsl
    from bsl.compiler import compile as bsl_compile

    spec = bsl.parse(source)
    output = bsl_compile(spec, target="pytest")

    for filename, content in output.files.items():
        Path(filename).write_text(content)

    print(f"Generated {output.test_count} test cases")
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from bsl.compiler.base import CompilerOutput, CompilerTarget
from bsl.compiler.pytest_target import PytestTarget

if TYPE_CHECKING:
    from bsl.ast.nodes import AgentSpec

_REGISTRY: dict[str, type[CompilerTarget]] = {
    "pytest": PytestTarget,
}


def compile(  # noqa: A001
    spec: "AgentSpec",
    target: str = "pytest",
) -> CompilerOutput:
    """Compile a parsed BSL ``AgentSpec`` into executable test code.

    Parameters
    ----------
    spec:
        A parsed and validated ``AgentSpec`` AST.
    target:
        The compilation target.  Currently only ``"pytest"`` is supported.

    Returns
    -------
    CompilerOutput
        A mapping of filename → generated Python source, plus metadata
        such as the total test count and any compiler warnings.

    Raises
    ------
    ValueError
        If ``target`` is not a registered compiler target.
    """
    if target not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY))
        raise ValueError(
            f"Unknown compiler target {target!r}. Available targets: {available}"
        )
    compiler_cls = _REGISTRY[target]
    compiler = compiler_cls()
    return compiler.compile(spec)


def available_targets() -> list[str]:
    """Return the list of registered compiler target names."""
    return sorted(_REGISTRY)


__all__ = [
    "compile",
    "available_targets",
    "CompilerOutput",
    "CompilerTarget",
    "PytestTarget",
]
