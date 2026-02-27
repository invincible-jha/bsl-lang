"""BSL NL (natural language) subpackage.

Contains tools for translating between natural language and BSL,
including the compiler bridge pipeline.
"""
from __future__ import annotations

from bsl.nl.compiler_bridge import CompilerBridge, CompilerBridgeResult

__all__ = [
    "CompilerBridge",
    "CompilerBridgeResult",
]
