#!/usr/bin/env python3
"""Example: BSL Formatting and Linting

Demonstrates formatting BSL specs to canonical style and running
the linter to surface quality issues.

Usage:
    python examples/03_formatting_linting.py

Requirements:
    pip install bsl-lang
"""
from __future__ import annotations

import bsl

UNFORMATTED_SPEC = '''
agent   ClinicalHelper  {
  version:"1.0"
  model:"gpt-4-turbo"
  owner: "health@example.com"
    behavior diagnose    {
      must:response contains "consult a doctor"
    confidence:>=80%
      audit:full
    }
  behavior  prescribe  {
    must: response contains "not medical advice"
    confidence:>=  95%
  }
}
'''

NEEDS_LINTING = '''
agent AnalysisAgent {
  version: "1.0"
  model: "gpt-4o"
  owner: "data@example.com"
  behavior analyse {
    must: response contains "result"
    confidence: >= 50%
  }
}
'''


def main() -> None:
    print(f"bsl-lang version: {bsl.__version__}")

    # Step 1: Format unformatted spec
    spec = bsl.parse(UNFORMATTED_SPEC)
    canonical = bsl.format(spec)
    print("Original (excerpt):")
    print("  " + UNFORMATTED_SPEC.strip()[:100])
    print("\nFormatted (canonical):")
    for line in canonical.split("\n")[:15]:
        print(f"  {line}")

    # Step 2: Idempotency check — formatting twice gives the same result
    twice = bsl.format(bsl.parse(canonical))
    is_idempotent = canonical == twice
    print(f"\nFormat is idempotent: {is_idempotent}")

    # Step 3: Lint for quality issues
    lint_spec = bsl.parse(NEEDS_LINTING)
    findings = bsl.lint(lint_spec, include_hints=True)
    print(f"\nLint findings for AnalysisAgent ({len(findings)}):")
    for finding in findings:
        print(f"  [{finding.severity}] line {finding.line}: {finding.message}")

    # Step 4: Lint without hints
    error_warnings_only = bsl.lint(lint_spec, include_hints=False)
    print(f"\nFindings without hints: {len(error_warnings_only)}")
    for finding in error_warnings_only:
        print(f"  [{finding.severity}] {finding.message}")


if __name__ == "__main__":
    main()
