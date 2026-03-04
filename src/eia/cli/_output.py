"""Shared output helpers for the EIA CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

console = Console()


def render_dataframe(
    df: pd.DataFrame,
    format: str = "table",
    output: str | None = None,
    max_rows: int = 100,
) -> None:
    """Render a DataFrame in the requested format."""
    if format == "csv":
        text = df.to_csv(index=False)
    elif format == "json":
        text = df.to_json(orient="records", indent=2, date_format="iso")
    else:
        _print_rich_table(df, max_rows=max_rows)
        return

    if output:
        Path(output).write_text(text)
        typer.echo(f"Written to {output}")
    else:
        typer.echo(text)


def render_result(
    result: Any,
    format: str = "table",
    output: str | None = None,
    max_rows: int = 100,
) -> None:
    """Render an eval result (DataFrame, Series, or scalar)."""
    if isinstance(result, pd.Series):
        result = result.to_frame()

    if isinstance(result, pd.DataFrame):
        if format == "csv":
            text = result.to_csv()
        elif format == "json":
            text = result.to_json(orient="records", indent=2, date_format="iso")
        else:
            _print_rich_table(result, max_rows=max_rows, show_index=True)
            return

        if output:
            Path(output).write_text(text)
            typer.echo(f"Written to {output}")
        else:
            typer.echo(text)
    else:
        text = str(result)
        if output:
            Path(output).write_text(text)
            typer.echo(f"Written to {output}")
        else:
            typer.echo(text)


def _print_rich_table(
    df: pd.DataFrame,
    max_rows: int = 100,
    show_index: bool = False,
) -> None:
    """Print a DataFrame as a Rich table."""
    table = Table()

    if show_index:
        idx_name = str(df.index.name or "")
        table.add_column(idx_name, style="cyan")

    for col in df.columns:
        table.add_column(str(col))

    for idx, row in df.head(max_rows).iterrows():
        values = []
        if show_index:
            values.append(str(idx))
        values += [_fmt(row[c]) for c in df.columns]
        table.add_row(*values)

    if len(df) > max_rows:
        table.caption = f"Showing {max_rows} of {len(df)} rows"

    console.print(table)


def _fmt(val: Any) -> str:
    """Format a value for table display."""
    if isinstance(val, float):
        return f"{val:.4f}"
    if val is None:
        return ""
    return str(val)
