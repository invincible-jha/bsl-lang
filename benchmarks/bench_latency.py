"""Benchmark: BSL parse latency (p50/p95/mean).

Measures per-call latency for BSL parse operations on various spec sizes.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import bsl

_WARMUP: int = 100
_ITERATIONS: int = 3_000

_MINIMAL_BSL = """
agent MinimalAgent {
  version: "1.0"
  model: "gpt-4o"
  owner: "test@example.com"

  behavior reply {
    must: response contains "ok"
    audit: none
  }
}
"""

_MEDIUM_BSL = """
agent MediumAgent {
  version: "2.0"
  model: "claude-3-5-sonnet"
  owner: "team@example.com"

  behavior search {
    must: response contains "result"
    must: response not contains "error"
    confidence: >= 75%
    audit: basic
  }

  behavior summarize {
    must: response.length <= 500
    confidence: >= 85%
    audit: basic
  }

  invariant no_pii {
    always: response not contains "email"
    severity: high
  }

  invariant cost_guard {
    always: cost <= 0.10
    severity: medium
  }
}
"""


def bench_parse_latency() -> dict[str, object]:
    """Benchmark BSL parse latency on a minimal spec.

    Returns
    -------
    dict with keys: operation, iterations, total_seconds, ops_per_second,
    avg_latency_ms, p50_ms, p95_ms.
    """
    # Warmup
    for _ in range(_WARMUP):
        bsl.parse(_MINIMAL_BSL)

    latencies_ms: list[float] = []
    for _ in range(_ITERATIONS):
        t0 = time.perf_counter()
        bsl.parse(_MINIMAL_BSL)
        latencies_ms.append((time.perf_counter() - t0) * 1000)

    sorted_lats = sorted(latencies_ms)
    n = len(sorted_lats)
    total = sum(latencies_ms) / 1000

    result: dict[str, object] = {
        "operation": "bsl_parse_latency_minimal",
        "iterations": _ITERATIONS,
        "total_seconds": round(total, 4),
        "ops_per_second": round(_ITERATIONS / total, 1),
        "avg_latency_ms": round(sum(latencies_ms) / n, 4),
        "p50_ms": round(sorted_lats[int(n * 0.50)], 4),
        "p95_ms": round(sorted_lats[min(int(n * 0.95), n - 1)], 4),
    }
    print(
        f"[bench_latency] {result['operation']}: "
        f"p50={result['p50_ms']:.4f}ms  p95={result['p95_ms']:.4f}ms  "
        f"mean={result['avg_latency_ms']:.4f}ms"
    )
    return result


if __name__ == "__main__":
    result = bench_parse_latency()
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    output_path = results_dir / "latency_baseline.json"
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print(f"Results saved to {output_path}")
