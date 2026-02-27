# bsl-lang

Behavioral Specification Language toolkit: parser, validator, formatter, linter

[![CI](https://github.com/aumos-ai/bsl-lang/actions/workflows/ci.yaml/badge.svg)](https://github.com/aumos-ai/bsl-lang/actions/workflows/ci.yaml)
[![PyPI version](https://img.shields.io/pypi/v/bsl-lang.svg)](https://pypi.org/project/bsl-lang/)
[![Python versions](https://img.shields.io/pypi/pyversions/bsl-lang.svg)](https://pypi.org/project/bsl-lang/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Part of the [AumOS](https://github.com/aumos-ai) open-source agent infrastructure portfolio.

---

## Features

- Formal EBNF grammar for agent behavior specifications — `behavior`, `invariant`, `degrades_to`, and `composition` blocks with `must`/`must_not`/`should`/`may` modal constraints
- Hand-written recursive-descent parser that produces a typed AST (`AgentSpec`, `BehaviorDecl`, `InvariantDecl`, and expression nodes) with source-span tracking
- Semantic validator with configurable rule sets and strict mode that promotes warnings to errors for CI gating
- AST serializer with round-trip JSON Schema output so specs can be consumed by external tooling
- Canonical formatter that enforces clause ordering within behavior and invariant blocks, preserving comments
- Linter with naming, completeness, and consistency rule sets (extensible via custom rule callables)
- CLI with `validate`, `fmt`, `lint`, and `diff` subcommands for use in pre-commit hooks and CI pipelines

## Quick Start

Install from PyPI:

```bash
pip install bsl-lang
```

Verify the installation:

```bash
bsl-lang version
```

Basic usage:

```python
import bsl

# See examples/01_quickstart.py for a working example
```

## Documentation

- [Architecture](docs/architecture.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Examples](examples/README.md)

## Enterprise Upgrade

For production deployments requiring SLA-backed support and advanced
integrations, contact the maintainers or see the commercial extensions documentation.

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md)
before opening a pull request.

## License

Apache 2.0 — see [LICENSE](LICENSE) for full terms.

---

Part of [AumOS](https://github.com/aumos-ai) — open-source agent infrastructure.
