"""Benchmark: Memory usage during BSL parse operations."""
from __future__ import annotations

import json
import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import bsl

_ITERATIONS: int = 500

_SAMPLE_BSL = """
agent MemBenchAgent {
  version: "1.0"
  model: "gpt-4o"
  owner: "bench@example.com"

  behavior respond {
    must: response contains "ok"
    confidence: >= 80%
    audit: basic
  }
}
"""


def bench_parse_memory() -> dict[str, object]:
    """Benchmark memory usage during BSL parse operations.

    Returns
    -------
    dict with keys: operation, iterations, peak_memory_kb, current_memory_kb.
    """
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    for _ in range(_ITERATIONS):
        bsl.parse(_SAMPLE_BSL)

    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot_after.compare_to(snapshot_before, "lineno")
    total_bytes = sum(stat.size_diff for stat in stats if stat.size_diff > 0)
    peak_kb = round(total_bytes / 1024, 2)

    result: dict[str, object] = {
        "operation": "bsl_parse_memory",
        "iterations": _ITERATIONS,
        "peak_memory_kb": peak_kb,
        "current_memory_kb": peak_kb,
        "ops_per_second": 0.0,
        "avg_latency_ms": 0.0,
    }
    print(f"[bench_memory] {result['operation']}: peak {peak_kb:.2f} KB over {_ITERATIONS} iterations")
    return result


if __name__ == "__main__":
    result = bench_parse_memory()
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    output_path = results_dir / "memory_baseline.json"
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print(f"Results saved to {output_path}")
