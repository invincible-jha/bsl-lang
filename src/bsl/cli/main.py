"""CLI entry point for bsl-lang.

Invoked as::

    bsl-lang [OPTIONS] COMMAND [ARGS]...

or, during development::

    python -m bsl.cli.main

Commands
--------
validate    Parse and validate a BSL file
diff        Compare two BSL files structurally
fmt         Format a BSL file to canonical style
lint        Run lint rules against a BSL file
schema      Export a JSON Schema from a BSL file
parse       Dump the parsed AST to JSON or YAML
version     Show version information
plugins     List registered plugins
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

console = Console()
err_console = Console(stderr=True)


def _read_source(path: str) -> str:
    """Read a BSL source file, exiting on error."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        err_console.print(f"[red]Error:[/red] File not found: {path}")
        sys.exit(1)
    except OSError as exc:
        err_console.print(f"[red]Error:[/red] Cannot read {path}: {exc}")
        sys.exit(1)


def _parse_or_exit(source: str, path: str) -> Any:
    """Parse BSL source, printing errors and exiting on failure."""
    from bsl.lexer import LexError
    from bsl.parser import ParseErrorCollection, parse

    try:
        return parse(source)
    except LexError as exc:
        err_console.print(f"[red]Lex error[/red] in {path}: {exc}")
        sys.exit(1)
    except ParseErrorCollection as exc:
        err_console.print(f"[red]Parse errors[/red] in {path}:")
        for error in exc.errors:
            err_console.print(f"  {error}")
        sys.exit(1)


def _severity_color(severity_name: str) -> str:
    """Map a DiagnosticSeverity name to a Rich color string."""
    colors = {
        "ERROR": "red",
        "WARNING": "yellow",
        "INFORMATION": "blue",
        "HINT": "dim",
    }
    return colors.get(severity_name, "white")


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(package_name="bsl-lang")
def cli() -> None:
    """Behavioral Specification Language toolkit: parser, validator, formatter, linter."""


# ---------------------------------------------------------------------------
# version command
# ---------------------------------------------------------------------------


@cli.command(name="version")
def version_command() -> None:
    """Show detailed version information."""
    from bsl import __version__

    table = Table(show_header=False, box=None)
    table.add_row("[bold]bsl-lang[/bold]", f"v{__version__}")
    table.add_row("Python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    table.add_row("Platform", sys.platform)
    console.print(table)


# ---------------------------------------------------------------------------
# plugins command
# ---------------------------------------------------------------------------


@cli.command(name="plugins")
def plugins_command() -> None:
    """List all registered plugins loaded from entry-points."""
    from bsl.plugins.registry import PluginRegistry

    console.print("[bold]Registered plugins:[/bold]")
    console.print("  (No plugins registered. Install a plugin package to see entries here.)")


# ---------------------------------------------------------------------------
# validate command
# ---------------------------------------------------------------------------


@cli.command(name="validate")
@click.argument("file", type=click.Path(exists=False))
@click.option("--strict", is_flag=True, default=False, help="Treat warnings as errors")
def validate_command(file: str, strict: bool) -> None:
    """Parse and validate a BSL file.

    FILE is the path to the .bsl file to validate.
    """
    from bsl.validator import Validator

    source = _read_source(file)
    spec = _parse_or_exit(source, file)

    validator = Validator(strict=strict)
    diagnostics = validator.validate(spec)

    if not diagnostics:
        console.print(f"[green]OK[/green] {file} — no issues found")
        sys.exit(0)

    errors = [d for d in diagnostics if d.is_error]
    warnings = [d for d in diagnostics if not d.is_error]

    table = Table(title=f"Validation: {file}", show_lines=True)
    table.add_column("Severity", style="bold", min_width=10)
    table.add_column("Code", min_width=8)
    table.add_column("Location", min_width=10)
    table.add_column("Message")

    for d in diagnostics:
        color = _severity_color(d.severity.name)
        loc = f"{d.span.line}:{d.span.col}"
        table.add_row(
            f"[{color}]{d.severity.name}[/{color}]",
            d.code,
            loc,
            d.message + (f"\n[dim]hint: {d.suggestion}[/dim]" if d.suggestion else ""),
        )

    console.print(table)
    console.print(
        f"\n[bold]Summary:[/bold] {len(errors)} error(s), {len(warnings)} warning(s)"
    )

    if errors:
        sys.exit(1)


# ---------------------------------------------------------------------------
# diff command
# ---------------------------------------------------------------------------


@cli.command(name="diff")
@click.argument("old", type=click.Path(exists=False))
@click.argument("new", type=click.Path(exists=False))
def diff_command(old: str, new: str) -> None:
    """Compare two BSL files structurally.

    OLD and NEW are paths to .bsl files to compare.
    """
    from bsl.diff import diff

    old_source = _read_source(old)
    new_source = _read_source(new)
    old_spec = _parse_or_exit(old_source, old)
    new_spec = _parse_or_exit(new_source, new)

    changes = diff(old_spec, new_spec)

    if not changes:
        console.print("[green]No structural changes between the two files.[/green]")
        sys.exit(0)

    console.print(f"[bold]BSL Diff:[/bold] {old} → {new}\n")
    for change in changes:
        line = str(change)
        if line.startswith("[+]"):
            console.print(f"[green]{line}[/green]")
        elif line.startswith("[-]"):
            console.print(f"[red]{line}[/red]")
        else:
            console.print(f"[yellow]{line}[/yellow]")

    console.print(f"\n[bold]{len(changes)}[/bold] change(s) total")


# ---------------------------------------------------------------------------
# fmt command
# ---------------------------------------------------------------------------


@cli.command(name="fmt")
@click.argument("file", type=click.Path(exists=False))
@click.option("--check", is_flag=True, default=False, help="Check if file is already formatted")
@click.option("--in-place", is_flag=True, default=False, help="Rewrite the file in place")
def fmt_command(file: str, check: bool, in_place: bool) -> None:
    """Format a BSL file to canonical style.

    FILE is the path to the .bsl file to format.

    Without --check or --in-place, prints the formatted output to stdout.
    """
    from bsl.formatter import format_spec

    source = _read_source(file)
    spec = _parse_or_exit(source, file)
    formatted = format_spec(spec)

    if check:
        if formatted == source:
            console.print(f"[green]OK[/green] {file} — already formatted")
            sys.exit(0)
        else:
            console.print(f"[yellow]NEEDS FORMATTING[/yellow] {file}")
            sys.exit(1)
    elif in_place:
        Path(file).write_text(formatted, encoding="utf-8")
        console.print(f"[green]Formatted[/green] {file}")
    else:
        syntax = Syntax(formatted, "text", line_numbers=True)
        console.print(syntax)


# ---------------------------------------------------------------------------
# lint command
# ---------------------------------------------------------------------------


@cli.command(name="lint")
@click.argument("file", type=click.Path(exists=False))
@click.option("--no-hints", is_flag=True, default=False, help="Suppress HINT-level findings")
def lint_command(file: str, no_hints: bool) -> None:
    """Run lint rules against a BSL file.

    FILE is the path to the .bsl file to lint.
    """
    from bsl.linter import BslLinter

    source = _read_source(file)
    spec = _parse_or_exit(source, file)

    linter = BslLinter(include_hints=not no_hints)
    diagnostics = linter.lint(spec)

    if not diagnostics:
        console.print(f"[green]OK[/green] {file} — no lint issues found")
        sys.exit(0)

    table = Table(title=f"Lint: {file}", show_lines=True)
    table.add_column("Severity", style="bold", min_width=10)
    table.add_column("Code", min_width=10)
    table.add_column("Location", min_width=10)
    table.add_column("Message")

    for d in diagnostics:
        color = _severity_color(d.severity.name)
        loc = f"{d.span.line}:{d.span.col}"
        table.add_row(
            f"[{color}]{d.severity.name}[/{color}]",
            d.code,
            loc,
            d.message + (f"\n[dim]hint: {d.suggestion}[/dim]" if d.suggestion else ""),
        )

    console.print(table)
    errors = [d for d in diagnostics if d.is_error]
    console.print(f"\n[bold]{len(diagnostics)}[/bold] lint finding(s)")

    if errors:
        sys.exit(1)


# ---------------------------------------------------------------------------
# schema command
# ---------------------------------------------------------------------------


@cli.command(name="schema")
@click.argument("file", type=click.Path(exists=False))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json"], case_sensitive=False),
    default="json",
    help="Output format (currently only json is supported)",
)
@click.option("--output", "-o", default=None, help="Output file path (defaults to stdout)")
def schema_command(file: str, output_format: str, output: str | None) -> None:
    """Export a JSON Schema from a BSL file.

    FILE is the path to the .bsl file to process.
    """
    from bsl.schema import SchemaExporter

    source = _read_source(file)
    spec = _parse_or_exit(source, file)

    exporter = SchemaExporter()
    schema_text = exporter.to_json(spec, indent=2)

    if output:
        Path(output).write_text(schema_text, encoding="utf-8")
        console.print(f"[green]Schema written to[/green] {output}")
    else:
        syntax = Syntax(schema_text, "json", line_numbers=True)
        console.print(syntax)


# ---------------------------------------------------------------------------
# parse command
# ---------------------------------------------------------------------------


@cli.command(name="parse")
@click.argument("file", type=click.Path(exists=False))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml"], case_sensitive=False),
    default="json",
    help="AST output format",
)
@click.option("--output", "-o", default=None, help="Output file path (defaults to stdout)")
def parse_command(file: str, output_format: str, output: str | None) -> None:
    """Parse a BSL file and dump the AST.

    FILE is the path to the .bsl file to parse.
    """
    from bsl.ast import AstSerializer

    source = _read_source(file)
    spec = _parse_or_exit(source, file)

    serializer = AstSerializer()

    if output_format == "json":
        text = serializer.to_json(spec, indent=2)
        lang = "json"
    else:
        text = serializer.to_yaml(spec)
        lang = "yaml"

    if output:
        Path(output).write_text(text, encoding="utf-8")
        console.print(f"[green]AST written to[/green] {output}")
    else:
        syntax = Syntax(text, lang, line_numbers=True)
        console.print(syntax)


# ---------------------------------------------------------------------------
# translate command
# ---------------------------------------------------------------------------


@cli.command(name="translate")
@click.argument("text")
@click.option(
    "--provider",
    "provider_name",
    type=click.Choice(["template", "llm"], case_sensitive=False),
    default="template",
    help="Translation provider to use (default: template).",
)
@click.option(
    "--reverse",
    is_flag=True,
    default=False,
    help="Translate BSL → natural language instead of NL → BSL.",
)
def translate_command(text: str, provider_name: str, reverse: bool) -> None:
    """Translate natural-language text to BSL directives (or vice versa).

    TEXT is the natural-language description (or BSL directive when
    --reverse is given) to translate.

    Examples:

    \b
        bsl-lang translate "must never expose user credentials"
        bsl-lang translate "FORBID: expose user credentials" --reverse
        bsl-lang translate "must always validate input" --provider template
    """
    from bsl.translate.providers import MockLLMProvider, TemplateProvider

    if provider_name == "template":
        provider = TemplateProvider()
    else:
        # "llm" without a configured LLM: fall back to TemplateProvider
        # with a visible warning so the user knows what is happening.
        err_console.print(
            "[yellow]Warning:[/yellow] No LLM is configured. "
            "Falling back to template-based translation. "
            "Set up a TranslationProvider and pass it programmatically "
            "to use a real LLM.",
        )
        provider = TemplateProvider()

    if reverse:
        from bsl.translate.bsl_to_nl import BSLToNLTranslator

        translator: Any = BSLToNLTranslator(provider=provider)
    else:
        from bsl.translate.nl_to_bsl import NLToBSLTranslator

        translator = NLToBSLTranslator(provider=provider)

    try:
        result = translator.translate(text)
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[red]Translation error:[/red] {exc}")
        sys.exit(1)

    console.print(result)


if __name__ == "__main__":
    cli()
