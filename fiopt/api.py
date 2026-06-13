"""FiOpt public API — the main entry points for programmatic use.

Usage:
    from fiopt import analyze, analyze_source

    # Analyze a file
    report = analyze("main.py")
    print(report.complexity)
    print(report.bottlenecks)
    print(report.suggestions)

    # Analyze source code directly
    report = analyze_source('''
    def bubble_sort(arr):
        for i in range(len(arr)):
            for j in range(len(arr) - 1):
                if arr[j] > arr[j+1]:
                    arr[j], arr[j+1] = arr[j+1], arr[j]
    ''')
"""

from __future__ import annotations

import ast
import time
from pathlib import Path

from fiopt.config import AnalysisConfig, ComplexityClass, Severity
from fiopt.parser.source_loader import load_file, scan_project, SourceFile
from fiopt.parser.ast_parser import parse, ParsedModule
from fiopt.analyzer.complexity_estimator import estimate_complexity
from fiopt.analyzer.pattern_matcher import detect_patterns
from fiopt.analyzer.dead_code_detector import detect_dead_code
from fiopt.analyzer.data_structure_analyzer import detect_data_structure_issues
from fiopt.reporting.report import (
    AnalysisReport,
    FileReport,
    FunctionReport,
)


def _determine_severity(
    func_report: FunctionReport, config: AnalysisConfig
) -> Severity:
    """Determine the severity level for a function based on its analysis."""
    c = func_report.complexity.estimated_complexity

    # Check complexity thresholds
    if c >= config.complexity_critical_threshold:
        return Severity.CRITICAL
    if c >= config.complexity_warning_threshold:
        return Severity.WARNING

    # Check anti-patterns
    if func_report.patterns:
        if func_report.patterns.critical_count > 0:
            return Severity.CRITICAL
        if func_report.patterns.warning_count > 0:
            return Severity.WARNING

    # Check data structure issues
    if func_report.data_structure and func_report.data_structure.issues:
        return Severity.WARNING

    # Check recursion warnings
    if func_report.complexity.warnings:
        return Severity.WARNING

    return Severity.INFO


def _analyze_file(
    source_file: SourceFile, config: AnalysisConfig
) -> FileReport:
    """Analyze a single source file."""
    file_report = FileReport(
        filepath=source_file.path,
        line_count=source_file.line_count,
    )

    # Parse
    try:
        parsed = parse(source_file.content, filename=str(source_file.path))
    except SyntaxError as e:
        file_report.parse_errors.append(f"SyntaxError: {e}")
        return file_report

    # Get all function names and nodes for cross-referencing
    all_functions_list = parsed.all_functions
    all_function_names = {f.name for f in all_functions_list}
    all_function_nodes = {f.name: f.node for f in all_functions_list}

    # Analyze each function
    for func_info in all_functions_list:
        # Skip very small functions (getters, properties, etc.)
        func_node = func_info.node

        # Complexity estimation
        complexity = estimate_complexity(
            func_node,
            all_function_names=all_function_names,
            all_functions=all_function_nodes,
        )

        # Anti-pattern detection
        patterns = None
        if config.detect_anti_patterns:
            patterns = detect_patterns(func_node)

        # Data structure analysis
        ds_analysis = None
        if config.detect_data_structure_issues:
            ds_analysis = detect_data_structure_issues(func_node)

        func_report = FunctionReport(
            name=func_info.name,
            lineno=func_info.lineno,
            end_lineno=func_info.end_lineno,
            line_count=func_info.body_line_count,
            complexity=complexity,
            patterns=patterns,
            data_structure=ds_analysis,
        )

        # Determine severity
        func_report.severity = _determine_severity(func_report, config)

        file_report.function_reports.append(func_report)

    # Dead code detection
    if config.detect_dead_code:
        func_nodes = [f.node for f in all_functions_list]
        file_report.dead_code = detect_dead_code(parsed.tree, func_nodes)

    return file_report


def analyze(
    path: str | Path,
    config: AnalysisConfig | None = None,
) -> AnalysisReport:
    """Analyze a Python file or directory.

    This is the primary API entry point for FiOpt.

    Args:
        path: Path to a Python file or directory.
        config: Optional analysis configuration.

    Returns:
        AnalysisReport with complete analysis results.

    Usage:
        >>> from fiopt import analyze
        >>> report = analyze("main.py")
        >>> print(report.complexity)
        >>> print(report.bottlenecks)
        >>> print(report.suggestions)
    """
    if config is None:
        config = AnalysisConfig()

    start_time = time.perf_counter()
    report = AnalysisReport()

    path = Path(path)
    if path.is_file():
        source = load_file(path)
        file_report = _analyze_file(source, config)
        report.files.append(file_report)
    elif path.is_dir():
        files = scan_project(
            path,
            extensions=config.file_extensions,
            exclude_dirs=config.exclude_dirs,
        )
        for source in files:
            file_report = _analyze_file(source, config)
            report.files.append(file_report)
    else:
        raise FileNotFoundError(f"Path not found: {path}")

    elapsed = (time.perf_counter() - start_time) * 1000
    report.analysis_duration_ms = elapsed

    return report


def analyze_source(
    source: str,
    filename: str = "<string>",
    config: AnalysisConfig | None = None,
) -> AnalysisReport:
    """Analyze Python source code from a string.

    Useful for testing or analyzing code snippets.

    Args:
        source: Python source code string.
        filename: Filename for error messages.
        config: Optional analysis configuration.

    Returns:
        AnalysisReport with complete analysis results.

    Usage:
        >>> from fiopt import analyze_source
        >>> report = analyze_source('''
        ... def sort_pairs(data):
        ...     for i in range(len(data)):
        ...         for j in range(len(data)):
        ...             if data[i] > data[j]:
        ...                 data[i], data[j] = data[j], data[i]
        ... ''')
        >>> print(report.complexity)
    """
    if config is None:
        config = AnalysisConfig()

    start_time = time.perf_counter()

    source_file = SourceFile(
        path=Path(filename),
        content=source,
        line_count=source.count("\n") + 1,
    )

    report = AnalysisReport()
    file_report = _analyze_file(source_file, config)
    report.files.append(file_report)

    elapsed = (time.perf_counter() - start_time) * 1000
    report.analysis_duration_ms = elapsed

    return report
