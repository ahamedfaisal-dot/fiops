"""Rich terminal output for FiOpt analysis reports.

Produces beautiful, color-coded terminal output with:
- Function complexity table
- Issue highlights
- Anti-pattern warnings
- Summary statistics
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from rich import box

from fiopt.config import ComplexityClass, Severity
from fiopt.reporting.report import AnalysisReport, FileReport, FunctionReport


# Color mapping for complexity classes
_COMPLEXITY_COLORS = {
    ComplexityClass.O_1: "green",
    ComplexityClass.O_LOG_N: "green",
    ComplexityClass.O_N: "cyan",
    ComplexityClass.O_N_LOG_N: "cyan",
    ComplexityClass.O_N_SQUARED: "yellow",
    ComplexityClass.O_N_CUBED: "red",
    ComplexityClass.O_N_K: "red",
    ComplexityClass.O_2_N: "bold red",
    ComplexityClass.O_N_FACTORIAL: "bold red",
    ComplexityClass.UNKNOWN: "dim",
}

_SEVERITY_COLORS = {
    Severity.INFO: "blue",
    Severity.WARNING: "yellow",
    Severity.CRITICAL: "red",
}

_SEVERITY_ICONS = {
    Severity.INFO: "[i]",
    Severity.WARNING: "[!]",
    Severity.CRITICAL: "[x]",
}


def render_terminal(report: AnalysisReport, verbose: bool = False) -> None:
    """Render an analysis report to the terminal using Rich.

    Args:
        report: The analysis report to render.
        verbose: If True, show detailed explanations.
    """
    import sys
    import os
    # Force UTF-8 output on Windows to avoid cp1252 emoji encoding errors.
    # We use os.fdopen with closefd=False to avoid closing the underlying stdout.
    if sys.platform == "win32" and hasattr(sys.stdout, "fileno"):
        try:
            fd = sys.stdout.fileno()
            utf8_stdout = os.fdopen(fd, mode="w", encoding="utf-8", errors="replace", closefd=False)
            console = Console(file=utf8_stdout)
        except (OSError, ValueError):
            # In test environments (Click CliRunner), fileno() may not work
            console = Console()
    else:
        console = Console()

    # Header
    console.print()
    console.print(
        Panel(
            "[bold bright_cyan]FiOpt[/] — AI-Powered Code Complexity & Optimization Engine",
            subtitle=f"v{report.fiopt_version}",
            border_style="bright_cyan",
        )
    )
    console.print()

    for file_report in report.files:
        _render_file(console, file_report, verbose)

    # Summary
    _render_summary(console, report)


def _render_file(
    console: Console, file_report: FileReport, verbose: bool
) -> None:
    """Render a single file's analysis."""
    # File header
    filepath = str(file_report.filepath)
    worst = file_report.worst_complexity
    color = _COMPLEXITY_COLORS.get(worst, "white")

    console.print(
        f"[bold]File: {filepath}[/] "
        f"({file_report.line_count} lines, "
        f"{file_report.total_functions} functions)"
    )
    console.print()

    if file_report.parse_errors:
        for err in file_report.parse_errors:
            console.print(f"  [red]Parse Error:[/] {err}")
        return

    if not file_report.function_reports:
        console.print("  [dim]No functions found to analyze.[/]")
        console.print()
        return

    # Function complexity table
    table = Table(
        title="Function Analysis",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold bright_cyan",
        border_style="dim",
        pad_edge=True,
    )
    table.add_column("Function", style="bold", min_width=20)
    table.add_column("Lines", justify="center", min_width=8)
    table.add_column("Complexity", justify="center", min_width=12)
    table.add_column("Confidence", justify="center", min_width=10)
    table.add_column("Issues", justify="center", min_width=8)
    table.add_column("Severity", justify="center", min_width=10)

    for func in file_report.functions_by_complexity:
        c = func.complexity.estimated_complexity
        color = _COMPLEXITY_COLORS.get(c, "white")
        sev_color = _SEVERITY_COLORS.get(func.severity, "white")
        sev_icon = _SEVERITY_ICONS.get(func.severity, "")

        table.add_row(
            func.name,
            f"L{func.lineno}-{func.end_lineno}",
            f"[{color}]{c.value}[/]",
            f"{func.complexity.confidence:.0%}",
            str(func.total_issues),
            f"[{sev_color}]{sev_icon} {func.severity.value.upper()}[/]",
        )

    console.print(table)
    console.print()

    # Detailed analysis for each function
    if verbose:
        for func in file_report.functions_by_complexity:
            _render_function_detail(console, func)

    # Anti-patterns and issues
    _render_issues(console, file_report)

    # Dead code
    if file_report.dead_code and file_report.dead_code.total > 0:
        _render_dead_code(console, file_report)

    console.print()


def _render_function_detail(console: Console, func: FunctionReport) -> None:
    """Render detailed analysis for a function."""
    c = func.complexity
    if not c.explanations:
        return

    tree = Tree(f"[bold]{func.name}[/] — {c.estimated_complexity.value}")

    for exp in c.explanations:
        color = _COMPLEXITY_COLORS.get(exp.complexity, "white")
        node = tree.add(f"[{color}]{exp.complexity.value}[/] {exp.description}")
        if exp.detail:
            node.add(f"[dim]{exp.detail}[/]")

    if c.warnings:
        warn_node = tree.add("[yellow]! Warnings[/]")
        for warning in c.warnings:
            warn_node.add(f"[yellow]{warning}[/]")

    console.print(tree)
    console.print()


def _render_issues(console: Console, file_report: FileReport) -> None:
    """Render anti-patterns and data structure issues."""
    issues_found = False

    for func in file_report.function_reports:
        # Anti-patterns
        if func.patterns and func.patterns.anti_patterns:
            if not issues_found:
                console.print("[bold yellow]! Anti-Patterns Detected[/]")
                issues_found = True

            for pattern in func.patterns.anti_patterns:
                sev_color = {
                    "info": "blue",
                    "warning": "yellow",
                    "critical": "red",
                }.get(pattern.severity.value, "white")

                console.print(
                    f"  [{sev_color}]●[/] [bold]{func.name}[/] L{pattern.lineno}: "
                    f"{pattern.description}"
                )
                console.print(
                    f"    [green]→ {pattern.suggestion}[/]"
                )
                console.print(
                    f"    [dim]Impact: {pattern.estimated_impact}[/]"
                )

        # Data structure issues
        if func.data_structure and func.data_structure.issues:
            if not issues_found:
                console.print("[bold yellow]! Data Structure Issues[/]")
                issues_found = True

            for issue in func.data_structure.issues:
                console.print(
                    f"  [yellow]●[/] [bold]{func.name}[/] L{issue.lineno}: "
                    f"{issue.description}"
                )
                console.print(
                    f"    [green]→ {issue.suggestion}[/]"
                )

    if issues_found:
        console.print()


def _render_dead_code(console: Console, file_report: FileReport) -> None:
    """Render dead code findings."""
    dc = file_report.dead_code
    if not dc or dc.total == 0:
        return

    console.print("[bold dim]Dead Code[/]")
    for item in dc.items:
        icon = {
            "unreachable": "[unreachable]",
            "unused_variable": "[unused var]",
            "unused_import": "[unused import]",
            "unused_function": "[unused func]",
        }.get(item.kind, "•")

        console.print(f"  {icon} L{item.lineno}: {item.description}")

    console.print()


def _render_summary(console: Console, report: AnalysisReport) -> None:
    """Render the overall summary."""
    worst = report.worst_complexity
    color = _COMPLEXITY_COLORS.get(worst, "white")

    summary_table = Table(
        box=box.SIMPLE_HEAVY,
        show_header=False,
        border_style="bright_cyan",
        pad_edge=True,
    )
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Value", justify="right")

    summary_table.add_row("Files Analyzed", str(report.total_files))
    summary_table.add_row("Functions Analyzed", str(report.total_functions))
    summary_table.add_row("Total Lines", str(report.total_lines))
    summary_table.add_row("Worst Complexity", f"[{color}]{worst.value}[/]")
    summary_table.add_row("Total Issues", str(report.total_issues))
    summary_table.add_row(
        "Analysis Time",
        f"{report.analysis_duration_ms:.1f}ms"
    )

    console.print(
        Panel(
            summary_table,
            title="[bold bright_cyan]Summary[/]",
            border_style="bright_cyan",
        )
    )

    # Top bottlenecks
    if report.bottlenecks:
        console.print()
        console.print("[bold red]Top Bottlenecks[/]")
        for i, b in enumerate(report.bottlenecks[:5], 1):
            console.print(f"  {i}. {b}")

    console.print()
