"""Test that the 3-line quickstart API works for bsl-lang."""
from __future__ import annotations


def test_quickstart_parse_import() -> None:
    import bsl

    assert callable(bsl.parse)
    assert callable(bsl.validate)


def test_quickstart_bsl_spec_import() -> None:
    from bsl import BslSpec

    spec = BslSpec()
    assert spec is not None


def test_quickstart_bsl_spec_default() -> None:
    from bsl import BslSpec

    spec = BslSpec()
    assert spec.ast is not None


def test_quickstart_bsl_spec_validate() -> None:
    from bsl import BslSpec

    spec = BslSpec()
    issues = spec.validate()
    assert isinstance(issues, list)


def test_quickstart_bsl_spec_format() -> None:
    from bsl import BslSpec

    spec = BslSpec()
    text = spec.format()
    assert isinstance(text, str)
    assert len(text) > 0


def test_quickstart_parse_and_validate() -> None:
    import bsl

    source = (
        "agent TestAgent {\n"
        '  version: "1.0"\n'
        '  owner: "test@example.com"\n'
        "}\n"
    )
    spec = bsl.parse(source)
    issues = bsl.validate(spec)
    assert isinstance(issues, list)


def test_quickstart_bsl_spec_repr() -> None:
    from bsl import BslSpec

    spec = BslSpec()
    assert "BslSpec" in repr(spec)
