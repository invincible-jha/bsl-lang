#!/usr/bin/env python3
"""Example: BslSpec Convenience Class

Demonstrates using the BslSpec convenience class to build, validate,
format, and export BSL specs programmatically.

Usage:
    python examples/06_bslspec_convenience.py

Requirements:
    pip install bsl-lang
"""
from __future__ import annotations

import bsl
from bsl import BslSpec

BSL_SOURCE_A = '''
agent FinancialAnalyst {
  version: "1.0"
  model: "gpt-4o"
  owner: "finance@example.com"
  behavior analyse_report {
    must: response contains "revenue"
    confidence: >= 90%
    audit: full
  }
}
'''

BSL_SOURCE_B = '''
agent FinancialAnalyst {
  version: "2.0"
  model: "gpt-4o"
  owner: "finance@example.com"
  behavior analyse_report {
    must: response contains "revenue"
    must: response contains "ebitda"
    confidence: >= 93%
    audit: full
  }
  behavior forecast {
    must: response contains "projection"
    confidence: >= 85%
  }
}
'''


def main() -> None:
    print(f"bsl-lang version: {bsl.__version__}")

    # Step 1: Use BslSpec to parse and inspect
    spec_a = BslSpec.from_string(BSL_SOURCE_A)
    print(f"Spec A: {spec_a.agent_name} v{spec_a.version}")
    print(f"  Behaviors: {spec_a.behavior_names()}")
    print(f"  Owner: {spec_a.owner}")
    print(f"  Model: {spec_a.model}")

    # Step 2: Validate via BslSpec
    issues = spec_a.validate()
    print(f"  Validation issues: {len(issues)}")

    # Step 3: Format via BslSpec
    formatted = spec_a.format()
    print(f"  Formatted ({len(formatted)} chars):")
    print("  " + formatted[:150].replace("\n", "\n  "))

    # Step 4: Diff two versions via BslSpec
    spec_b = BslSpec.from_string(BSL_SOURCE_B)
    changes = spec_a.diff(spec_b)
    print(f"\nDiff A -> B: {len(changes)} change(s)")
    for change in changes:
        print(f"  [{change.change_type}] {change.path}")

    # Step 5: Export schema via BslSpec
    schema = spec_b.export_schema()
    print(f"\nSchema for v{spec_b.version}: "
          f"title='{schema.get('title', spec_b.agent_name)}'")

    # Step 6: Lint via BslSpec
    findings = spec_a.lint()
    print(f"Lint findings: {len(findings)}")
    for finding in findings[:3]:
        print(f"  [{finding.severity}] {finding.message[:65]}")


if __name__ == "__main__":
    main()
