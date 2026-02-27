# bsl-lang

**Behavioral Specification Language** — define, validate, and lint agent behavioral contracts.

[![CI](https://github.com/invincible-jha/bsl-lang/actions/workflows/ci.yaml/badge.svg)](https://github.com/invincible-jha/bsl-lang/actions/workflows/ci.yaml)
[![PyPI version](https://img.shields.io/pypi/v/bsl-lang.svg)](https://pypi.org/project/bsl-lang/)
[![Python versions](https://img.shields.io/pypi/pyversions/bsl-lang.svg)](https://pypi.org/project/bsl-lang/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/invincible-jha/bsl-lang/blob/main/LICENSE)

bsl-lang is a formal language toolkit for writing, parsing, validating, and linting behavioral contracts for AI agents. It gives teams a machine-readable way to express what an agent must, must not, should, and may do — and to enforce those constraints in CI pipelines.

## Installation

```bash
pip install bsl-lang
```

Verify the installation:

```bash
bsl-lang version
```

## Quick Start

```python
import bsl
from bsl.parser import Parser
from bsl.validator import Validator
from bsl.linter import Linter

# Parse a BSL specification from a string
source = """
behavior ResearchAgent {
  must call_tool("search") before responding
  must_not expose pii_data
  should cite_sources
  may ask_clarifying_questions
}

invariant SafeOutputs {
  must output.content not contains sensitive_patterns
}
"""

parser = Parser()
spec = parser.parse(source)

# Validate the spec
validator = Validator(strict=True)
result = validator.validate(spec)
if result.errors:
    for error in result.errors:
        print(f"Error: {error}")

# Run the linter
linter = Linter()
findings = linter.lint(spec)
for finding in findings:
    print(f"{finding.severity}: {finding.message}")
```

You can also use the CLI directly in pre-commit hooks and CI:

```bash
# Validate a spec file
bsl-lang validate agent_spec.bsl

# Format a spec file
bsl-lang fmt agent_spec.bsl

# Lint for naming and completeness issues
bsl-lang lint agent_spec.bsl

# Diff two spec versions
bsl-lang diff agent_spec_v1.bsl agent_spec_v2.bsl
```

## Key Features

- **Formal EBNF grammar** — `behavior`, `invariant`, `degrades_to`, and `composition` blocks with `must`/`must_not`/`should`/`may` modal constraints
- **Recursive-descent parser** — produces a typed AST with source-span tracking for precise error messages
- **Semantic validator** — configurable rule sets and strict mode that promotes warnings to errors for CI gating
- **JSON Schema output** — round-trip serializer so specs can be consumed by external tooling
- **Canonical formatter** — enforces clause ordering within blocks, preserving comments
- **Extensible linter** — naming, completeness, and consistency rule sets, extensible via custom rule callables
- **CLI toolchain** — `validate`, `fmt`, `lint`, and `diff` subcommands ready for pre-commit and CI integration

## Links

- [GitHub Repository](https://github.com/invincible-jha/bsl-lang)
- [PyPI Package](https://pypi.org/project/bsl-lang/)
- [Architecture](architecture.md)
- [Contributing](https://github.com/invincible-jha/bsl-lang/blob/main/CONTRIBUTING.md)
- [Changelog](https://github.com/invincible-jha/bsl-lang/blob/main/CHANGELOG.md)

---

Part of the [AumOS](https://github.com/aumos-ai) open-source agent infrastructure portfolio.
