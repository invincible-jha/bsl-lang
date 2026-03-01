#!/usr/bin/env python3
"""Example: Quickstart — bsl-lang

Minimal working example: parse a BSL spec, validate it,
format it, and lint for quality issues.

Usage:
    python examples/01_quickstart.py

Requirements:
    pip install bsl-lang
"""
from __future__ import annotations

import bsl

BSL_SOURCE = '''
agent GreetingAgent {
  version: "1.0"
  model: "gpt-4o"
  owner: "ai-team@example.com"
  behavior greet {
    must: response contains "Hello"
    confidence: >= 90%
    audit: basic
  }
  behavior farewell {
    must: response contains "Goodbye"
    confidence: >= 85%
  }
}
'''


def main() -> None:
    print(f"bsl-lang version: {bsl.__version__}")

    # Step 1: Parse BSL source into an AST
    spec = bsl.parse(BSL_SOURCE)
    print(f"Parsed agent: '{spec.name}', "
          f"version={spec.version}, "
          f"behaviors={len(spec.behaviors)}")

    # Step 2: Validate the spec
    diagnostics = bsl.validate(spec)
    errors = [d for d in diagnostics if d.severity == "error"]
    warnings = [d for d in diagnostics if d.severity == "warning"]
    print(f"Validation: {len(errors)} errors, {len(warnings)} warnings")
    for diag in diagnostics:
        print(f"  [{diag.severity}] {diag.message}")

    # Step 3: Format to canonical style
    canonical = bsl.format(spec)
    print(f"\nFormatted spec ({len(canonical)} chars):")
    print(canonical[:200])

    # Step 4: Lint for quality issues
    findings = bsl.lint(spec)
    print(f"Lint findings: {len(findings)}")
    for finding in findings[:3]:
        print(f"  [{finding.severity}] {finding.message}")


if __name__ == "__main__":
    main()
