"""Benchmark: BSL parse and test generation throughput.

Measures how many BSL parse operations and test generation passes can
complete per second using the public bsl.parse() and ComplianceTestGenerator APIs.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import bsl
from bsl.testgen.generator import ComplianceTestGenerator, TestGenConfig

_ITERATIONS: int = 5_000
_TESTGEN_ITERATIONS: int = 2_000

_SAMPLE_BSL = """
agent BenchmarkAgent {
  version: "1.0"
  model: "gpt-4o"
  owner: "bench@example.com"

  behavior respond {
    must: response contains "answer"
    confidence: >= 80%
    audit: basic
  }

  invariant no_pii {
    always: response not contains "ssn"
    severity: high
  }
}
"""


def bench_parse_throughput() -> dict[str, object]:
    """Benchmark BSL spec parsing throughput.

    Returns
    -------
    dict with keys: operation, iterations, total_seconds, ops_per_second,
    avg_latency_ms.
    """
    start = time.perf_counter()
    for _ in range(_ITERATIONS):
        bsl.parse(_SAMPLE_BSL)
    total = time.perf_counter() - start

    result: dict[str, object] = {
        "operation": "bsl_parse_throughput",
        "iterations": _ITERATIONS,
        "total_seconds": round(total, 4),
        "ops_per_second": round(_ITERATIONS / total, 1),
        "avg_latency_ms": round(total / _ITERATIONS * 1000, 4),
    }
    print(
        f"[bench_throughput] {result['operation']}: "
        f"{result['ops_per_second']:,.0f} ops/sec  "
        f"avg {result['avg_latency_ms']:.4f} ms"
    )
    return result


def bench_testgen_throughput() -> dict[str, object]:
    """Benchmark test generation speed from a parsed BSL spec.

    Returns
    -------
    dict with keys: operation, iterations, total_seconds, ops_per_second,
    avg_latency_ms.
    """
    spec = bsl.parse(_SAMPLE_BSL)
    config = TestGenConfig(include_behaviors=True, include_invariants=True)
    generator = ComplianceTestGenerator(config)

    start = time.perf_counter()
    for _ in range(_TESTGEN_ITERATIONS):
        generator.generate(spec)
    total = time.perf_counter() - start

    result: dict[str, object] = {
        "operation": "bsl_testgen_throughput",
        "iterations": _TESTGEN_ITERATIONS,
        "total_seconds": round(total, 4),
        "ops_per_second": round(_TESTGEN_ITERATIONS / total, 1),
        "avg_latency_ms": round(total / _TESTGEN_ITERATIONS * 1000, 4),
    }
    print(
        f"[bench_throughput] {result['operation']}: "
        f"{result['ops_per_second']:,.0f} ops/sec  "
        f"avg {result['avg_latency_ms']:.4f} ms"
    )
    return result


if __name__ == "__main__":
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    for bench_fn, fname in [
        (bench_parse_throughput, "parse_throughput_baseline.json"),
        (bench_testgen_throughput, "testgen_throughput_baseline.json"),
    ]:
        result = bench_fn()
        output_path = results_dir / fname
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        print(f"Results saved to {output_path}")
