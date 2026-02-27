"""Document formatting utilities for BSL exporters.

Provides pure functions for building structured markdown and text
documents from strings and structured data.
"""
from __future__ import annotations

import textwrap
from datetime import datetime


def heading(text: str, level: int = 1) -> str:
    """Return a markdown heading string.

    Parameters
    ----------
    text:
        Heading content.
    level:
        Heading level 1-6 (ATX-style ``#`` prefix).
    """
    level = max(1, min(6, level))
    return f"{'#' * level} {text}"


def bullet_list(items: list[str], indent: int = 0) -> str:
    """Return a markdown bullet list from *items*.

    Parameters
    ----------
    items:
        List of string items to render.
    indent:
        Leading spaces before each bullet.
    """
    if not items:
        return ""
    prefix = " " * indent
    return "\n".join(f"{prefix}- {item}" for item in items)


def code_block(content: str, language: str = "") -> str:
    """Return a fenced markdown code block.

    Parameters
    ----------
    content:
        Text to place inside the fence.
    language:
        Optional language identifier for syntax highlighting.
    """
    fence = "```"
    return f"{fence}{language}\n{content}\n{fence}"


def horizontal_rule() -> str:
    """Return a markdown horizontal rule."""
    return "---"


def bold(text: str) -> str:
    """Return *text* wrapped in bold markdown markers."""
    return f"**{text}**"


def italic(text: str) -> str:
    """Return *text* wrapped in italic markdown markers."""
    return f"_{text}_"


def table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a GitHub-Flavored Markdown table.

    Parameters
    ----------
    headers:
        Column header strings.
    rows:
        Data rows; each inner list must have the same length as *headers*.
    """
    if not headers:
        return ""

    col_widths = [len(h) for h in headers]
    for row in rows:
        for col_idx, cell in enumerate(row):
            if col_idx < len(col_widths):
                col_widths[col_idx] = max(col_widths[col_idx], len(cell))

    def _pad(value: str, width: int) -> str:
        return value.ljust(width)

    separator_row = ["-" * width for width in col_widths]
    header_line = "| " + " | ".join(_pad(h, col_widths[i]) for i, h in enumerate(headers)) + " |"
    sep_line = "| " + " | ".join(separator_row) + " |"
    data_lines = [
        "| " + " | ".join(_pad(cell, col_widths[ci]) for ci, cell in enumerate(row)) + " |"
        for row in rows
    ]
    return "\n".join([header_line, sep_line] + data_lines)


def wrap_paragraph(text: str, width: int = 80) -> str:
    """Wrap *text* to *width* characters per line.

    Parameters
    ----------
    text:
        Paragraph text to wrap.
    width:
        Maximum line width.
    """
    return textwrap.fill(text, width=width)


def format_timestamp(dt: datetime) -> str:
    """Return a human-readable UTC timestamp string.

    Parameters
    ----------
    dt:
        The datetime to format.
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def section(title: str, content: str, level: int = 2) -> str:
    """Return a full markdown section with heading and content.

    Parameters
    ----------
    title:
        Section heading text.
    content:
        Body text following the heading.
    level:
        Heading level.
    """
    parts = [heading(title, level)]
    if content.strip():
        parts.append("")
        parts.append(content.strip())
    return "\n".join(parts)


__all__ = [
    "bold",
    "bullet_list",
    "code_block",
    "format_timestamp",
    "heading",
    "horizontal_rule",
    "italic",
    "section",
    "table",
    "wrap_paragraph",
]
