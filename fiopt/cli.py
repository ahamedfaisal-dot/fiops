"""FiOpt CLI — Command-line interface.

Usage:
    fiopt analyze app.py
    fiopt analyze src/ --format html --output report.html
    fiopt analyze app.py --format json
    fiopt version
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from fiopt import __version__
from fiopt.config import AnalysisConfig, ReportFormat


@click.group()
@click.version_option(version=__version__, prog_name="FiOpt")
def main() -> None:
    """FiOpt — AI-Powered Code Complexity & Optimization Engine.

    Analyze Python code for algorithmic complexity, detect bottlenecks,
    and get optimization suggestions.
    """
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--format", "-f",
    "output_format",
    type=click.Choice(["terminal", "html", "json"], case_sensitive=False),
    default="terminal",
    help="Output format (default: terminal).",
)
@click.option(
    "--output", "-o",
    "output_path",
    type=click.Path(),
    default=None,
    help="Output file path (for html/json formats).",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Show detailed complexity explanations.",
)
@click.option(
    "--no-dead-code",
    is_flag=True,
    default=False,
    help="Skip dead code detection.",
)
@click.option(
    "--no-patterns",
    is_flag=True,
    default=False,
    help="Skip anti-pattern detection.",
)
@click.option(
    "--threshold",
    type=click.Choice(["O(n)", "O(n²)", "O(n³)"], case_sensitive=False),
    default="O(n²)",
    help="Complexity threshold for warnings (default: O(n²)).",
)
def analyze(
    path: str,
    output_format: str,
    output_path: str | None,
    verbose: bool,
    no_dead_code: bool,
    no_patterns: bool,
    threshold: str,
) -> None:
    """Analyze Python code for complexity and bottlenecks.

    PATH can be a Python file or a directory.

    Examples:

        fiopt analyze app.py

        fiopt analyze src/ --format html -o report.html

        fiopt analyze app.py -v --format json -o results.json
    """
    from fiopt.config import ComplexityClass
    from fiopt.api import analyze as do_analyze

    # Map threshold string to ComplexityClass
    threshold_map = {
        "O(n)": ComplexityClass.O_N,
        "O(n²)": ComplexityClass.O_N_SQUARED,
        "O(n³)": ComplexityClass.O_N_CUBED,
    }

    config = AnalysisConfig(
        detect_dead_code=not no_dead_code,
        detect_anti_patterns=not no_patterns,
        verbose=verbose,
        complexity_warning_threshold=threshold_map.get(
            threshold, ComplexityClass.O_N_SQUARED
        ),
    )

    try:
        report = do_analyze(path, config=config)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error during analysis: {e}", err=True)
        sys.exit(1)

    # Output
    if output_format == "terminal":
        from fiopt.reporting.terminal_reporter import render_terminal
        render_terminal(report, verbose=verbose)

    elif output_format == "html":
        from fiopt.reporting.html_reporter import save_html_report
        if output_path is None:
            output_path = "fiopt_report.html"
        saved = save_html_report(report, output_path)
        click.echo(f"HTML report saved to: {saved}")

    elif output_format == "json":
        from fiopt.reporting.json_reporter import render_json, save_json_report
        if output_path:
            saved = save_json_report(report, output_path)
            click.echo(f"JSON report saved to: {saved}")
        else:
            click.echo(render_json(report))

    # Exit code: non-zero if critical issues found
    critical = sum(
        1 for f in report.files
        for func in f.function_reports
        if func.severity.value == "critical"
    )
    if critical > 0:
        sys.exit(1)


@main.command()
def version() -> None:
    """Show FiOpt version and system information."""
    import platform
    click.echo(f"FiOpt v{__version__}")
    click.echo(f"Python {platform.python_version()}")
    click.echo(f"Platform: {platform.platform()}")


if __name__ == "__main__":
    main()
