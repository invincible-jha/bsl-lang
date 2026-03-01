#!/usr/bin/env python3
"""Example: Multi-Agent BSL Specifications

Demonstrates defining and validating BSL specs for multiple agents
in a pipeline, diffing them, and cross-checking constraints.

Usage:
    python examples/07_multi_agent_specs.py

Requirements:
    pip install bsl-lang
"""
from __future__ import annotations

import bsl
from bsl import BslSpec

AGENT_SPECS = {
    "fetcher": '''
agent DataFetcher {
  version: "1.0"
  model: "gpt-4o-mini"
  owner: "pipeline@example.com"
  behavior fetch_documents {
    must: response is json
    must: response contains "documents"
    confidence: >= 95%
    latency: <= 500ms
  }
}
''',
    "analyser": '''
agent ContentAnalyser {
  version: "1.0"
  model: "gpt-4o"
  owner: "pipeline@example.com"
  behavior analyse {
    must: response contains "findings"
    must: response length <= 2000 words
    confidence: >= 90%
    latency: <= 3000ms
    audit: full
  }
}
''',
    "summariser": '''
agent ExecutiveSummariser {
  version: "1.0"
  model: "claude-3-5-sonnet"
  owner: "pipeline@example.com"
  behavior summarise {
    must: response length <= 300 words
    must: response contains "key findings"
    confidence: >= 92%
    latency: <= 2000ms
    audit: full
  }
}
''',
}


def main() -> None:
    print(f"bsl-lang version: {bsl.__version__}")

    # Parse and validate all agents in the pipeline
    parsed_specs: dict[str, BslSpec] = {}
    print("Pipeline agents:")
    for agent_key, source in AGENT_SPECS.items():
        spec = BslSpec.from_string(source)
        issues = spec.validate()
        errors = [i for i in issues if i.severity == "error"]
        print(f"  {spec.agent_name} v{spec.version}: "
              f"behaviors={spec.behavior_names()}, "
              f"errors={len(errors)}")
        parsed_specs[agent_key] = spec

    # Cross-check latency budget across the pipeline
    print("\nLatency constraints (pipeline budget):")
    total_max_latency = 0
    for agent_key, spec in parsed_specs.items():
        for behavior in spec.ast.behaviors:
            latency = getattr(behavior, "latency_ms", None)
            if latency is not None:
                total_max_latency += latency
                print(f"  {spec.agent_name}.{behavior.name}: "
                      f"latency<={latency}ms")
    print(f"  Total max pipeline latency: {total_max_latency}ms")

    # Diff fetcher spec against analyser (cross-agent comparison)
    fetcher = parsed_specs["fetcher"]
    analyser = parsed_specs["analyser"]
    changes = fetcher.diff(analyser)
    print(f"\nDiff Fetcher -> Analyser: {len(changes)} structural differences")
    for change in changes[:5]:
        print(f"  [{change.change_type}] {change.path}")

    # Export schemas for all agents
    print("\nJSON Schema exports:")
    for agent_key, spec in parsed_specs.items():
        schema = spec.export_schema()
        title = schema.get("title", spec.agent_name)
        print(f"  {title}: {len(schema)} top-level keys")


if __name__ == "__main__":
    main()
