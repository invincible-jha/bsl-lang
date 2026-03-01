#!/usr/bin/env python3
"""Example: JSON Schema Export and Compilation

Demonstrates exporting a BSL spec as a JSON Schema document and
compiling it to pytest test stubs.

Usage:
    python examples/05_schema_export.py

Requirements:
    pip install bsl-lang
"""
from __future__ import annotations

import json

import bsl

BSL_SOURCE = '''
agent CustomerSupportAgent {
  version: "1.0"
  model: "gpt-4o-mini"
  owner: "support@example.com"
  behavior handle_complaint {
    must: response contains "apologise"
    must: response contains "resolve"
    confidence: >= 88%
    latency: <= 2000ms
    audit: full
  }
  behavior provide_faq {
    must: response is not empty
    confidence: >= 95%
    latency: <= 1000ms
  }
}
'''


def main() -> None:
    print(f"bsl-lang version: {bsl.__version__}")

    spec = bsl.parse(BSL_SOURCE)
    print(f"Agent: {spec.name} v{spec.version}")
    print(f"Behaviors: {[b.name for b in spec.behaviors]}")

    # Step 1: Export as JSON Schema
    schema = bsl.export_schema(spec)
    print(f"\nJSON Schema (draft version): {schema.get('$schema', 'unknown')}")
    print(f"Schema title: {schema.get('title', spec.name)}")
    print(f"Schema properties: {list(schema.get('properties', {}).keys())[:5]}")
    print(f"\nFull schema (formatted):")
    print(json.dumps(schema, indent=2)[:500])

    # Step 2: Compile to pytest test stubs
    try:
        output = bsl.compile(spec, target="pytest")
        print(f"\nCompiled to pytest:")
        print(f"  Files generated: {len(output.files)}")
        for filename, content in list(output.files.items())[:2]:
            print(f"\n  {filename}:")
            print("  " + content[:200].replace("\n", "\n  "))
    except Exception as error:
        print(f"\nCompile: {error}")


if __name__ == "__main__":
    main()
