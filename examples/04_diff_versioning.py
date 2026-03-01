#!/usr/bin/env python3
"""Example: BSL Spec Diffing and Versioning

Demonstrates computing structural diffs between two BSL spec
versions to track changes over time.

Usage:
    python examples/04_diff_versioning.py

Requirements:
    pip install bsl-lang
"""
from __future__ import annotations

import bsl

SPEC_V1 = '''
agent ReportAgent {
  version: "1.0"
  model: "gpt-4o"
  owner: "reports@example.com"
  behavior generate {
    must: response length <= 1000 words
    confidence: >= 85%
    audit: basic
  }
}
'''

SPEC_V2 = '''
agent ReportAgent {
  version: "2.0"
  model: "claude-3-5-sonnet"
  owner: "reports@example.com"
  behavior generate {
    must: response length <= 800 words
    must: response contains "executive summary"
    confidence: >= 90%
    audit: full
  }
  behavior summarise {
    must: response length <= 200 words
    confidence: >= 88%
  }
}
'''


def main() -> None:
    print(f"bsl-lang version: {bsl.__version__}")

    spec_v1 = bsl.parse(SPEC_V1)
    spec_v2 = bsl.parse(SPEC_V2)

    print(f"v1: model={spec_v1.model}, behaviors={len(spec_v1.behaviors)}")
    print(f"v2: model={spec_v2.model}, behaviors={len(spec_v2.behaviors)}")

    # Compute diff
    changes = bsl.diff(spec_v1, spec_v2)
    print(f"\nDiff: {len(changes)} change(s)")
    for change in changes:
        print(f"  [{change.change_type}] {change.path}")
        if hasattr(change, "old_value") and change.old_value is not None:
            print(f"    old: {str(change.old_value)[:60]}")
        if hasattr(change, "new_value") and change.new_value is not None:
            print(f"    new: {str(change.new_value)[:60]}")

    # Summarise changes by type
    added = [c for c in changes if c.change_type == "added"]
    modified = [c for c in changes if c.change_type == "modified"]
    removed = [c for c in changes if c.change_type == "removed"]
    print(f"\nSummary: added={len(added)}, "
          f"modified={len(modified)}, "
          f"removed={len(removed)}")

    # Self-diff (should produce zero changes)
    same_diff = bsl.diff(spec_v1, spec_v1)
    print(f"\nSelf-diff: {len(same_diff)} changes (expected 0)")


if __name__ == "__main__":
    main()
