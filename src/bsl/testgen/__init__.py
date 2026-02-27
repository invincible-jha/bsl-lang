"""BSL Compliance Test Generator package.

Exports :class:`ComplianceTestGenerator` for converting BSL invariants
and behavior constraints into runnable pytest test stubs.
"""
from __future__ import annotations

from bsl.testgen.generator import (
    ComplianceTestGenerator,
    GeneratedTest,
    TestGenConfig,
    TestGenResult,
)

__all__ = [
    "ComplianceTestGenerator",
    "GeneratedTest",
    "TestGenConfig",
    "TestGenResult",
]
