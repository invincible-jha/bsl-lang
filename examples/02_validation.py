#!/usr/bin/env python3
"""Example: BSL Validation

Demonstrates validating BSL specifications in normal and strict
modes, and interpreting diagnostic messages.

Usage:
    python examples/02_validation.py

Requirements:
    pip install bsl-lang
"""
from __future__ import annotations

import bsl

VALID_SPEC = '''
agent DocumentSummariser {
  version: "2.0"
  model: "claude-3-sonnet"
  owner: "nlp-team@example.com"
  behavior summarise {
    must: response length <= 500 words
    must: response contains "summary"
    confidence: >= 92%
    latency: <= 3000ms
    audit: full
  }
  behavior extract_entities {
    must: response is json
    confidence: >= 88%
  }
}
'''

INVALID_SPEC = '''
agent BadAgent {
  behavior incomplete_behavior {
    must: response contains "ok"
  }
}
'''


def print_diagnostics(label: str, diagnostics: list[object]) -> None:
    print(f"\n{label} ({len(diagnostics)} diagnostics):")
    if not diagnostics:
        print("  No issues found.")
        return
    for diag in diagnostics:
        print(f"  [{diag.severity}] line {diag.line}: {diag.message}")  # type: ignore[union-attr]


def main() -> None:
    print(f"bsl-lang version: {bsl.__version__}")

    # Validate a well-formed spec
    valid_spec = bsl.parse(VALID_SPEC)
    print_diagnostics("Valid spec (normal mode)", bsl.validate(valid_spec))
    print_diagnostics("Valid spec (strict mode)", bsl.validate(valid_spec, strict=True))

    # Validate a spec with issues
    try:
        invalid_spec = bsl.parse(INVALID_SPEC)
        print_diagnostics("Invalid spec", bsl.validate(invalid_spec))
    except Exception as error:
        print(f"\nParse error: {error}")

    # Inspect a valid spec's behaviors
    print(f"\nDocumentSummariser behaviors:")
    for behavior in valid_spec.behaviors:
        print(f"  {behavior.name}:")
        for constraint in behavior.constraints:
            print(f"    must: {constraint.expression}")
        if hasattr(behavior, "confidence"):
            print(f"    confidence: {behavior.confidence}")


if __name__ == "__main__":
    main()
