"""Structural tests for bsl-lang benchmark module."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "benchmarks"))


def test_bench_throughput_importable() -> None:
    """Verify bench_throughput module can be imported."""
    mod = importlib.import_module("bench_throughput")
    assert hasattr(mod, "bench_parse_throughput")
    assert hasattr(mod, "bench_testgen_throughput")


def test_bench_latency_importable() -> None:
    """Verify bench_latency module can be imported."""
    mod = importlib.import_module("bench_latency")
    assert hasattr(mod, "bench_parse_latency")


def test_bench_memory_importable() -> None:
    """Verify bench_memory module can be imported."""
    mod = importlib.import_module("bench_memory")
    assert hasattr(mod, "bench_parse_memory")


def test_parse_throughput_returns_expected_keys() -> None:
    """Verify bench_parse_throughput returns expected result keys."""
    from bench_throughput import bench_parse_throughput

    result = bench_parse_throughput()
    assert "operation" in result
    assert "iterations" in result
    assert "ops_per_second" in result
    assert "avg_latency_ms" in result
    assert float(result["ops_per_second"]) > 0  # type: ignore[arg-type]


def test_testgen_throughput_returns_expected_keys() -> None:
    """Verify bench_testgen_throughput returns expected result keys."""
    from bench_throughput import bench_testgen_throughput

    result = bench_testgen_throughput()
    assert "operation" in result
    assert "ops_per_second" in result
    assert "avg_latency_ms" in result
