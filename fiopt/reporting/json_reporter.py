"""JSON report generation for FiOpt analysis.

Produces structured, machine-readable JSON output suitable for:
- CI/CD pipeline integration
- Programmatic consumption
- Data analysis
"""

from __future__ import annotations

import json
from pathlib import Path

from fiopt.reporting.report import AnalysisReport, FileReport, FunctionReport


def _serialize_function(func: FunctionReport) -> dict:
    """Serialize a FunctionReport to a dict."""
    result = {
        "name": func.name,
        "lineno": func.lineno,
        "end_lineno": func.end_lineno,
        "line_count": func.line_count,
        "complexity": {
            "estimated": func.complexity.estimated_complexity.value,
            "confidence": round(func.complexity.confidence, 2),
            "explanations": [
                {
                    "source": e.source,
                    "complexity": e.complexity.value,
                    "lineno": e.lineno,
                    "description": e.description,
                    "detail": e.detail,
                }
                for e in func.complexity.explanations
            ],
            "bottleneck_lines": func.complexity.bottleneck_lines,
            "bottleneck_description": func.complexity.bottleneck_description,
            "warnings": func.complexity.warnings,
        },
        "severity": func.severity.value,
        "total_issues": func.total_issues,
    }

    # Anti-patterns
    if func.patterns and func.patterns.anti_patterns:
        result["anti_patterns"] = [
            {
                "name": p.name,
                "category": p.category.value,
                "severity": p.severity.value,
                "lineno": p.lineno,
                "description": p.description,
                "suggestion": p.suggestion,
                "estimated_impact": p.estimated_impact,
            }
            for p in func.patterns.anti_patterns
        ]

    # Data structure issues
    if func.data_structure and func.data_structure.issues:
        result["data_structure_issues"] = [
            {
                "variable": issue.variable_name,
                "current_type": issue.current_type,
                "suggested_type": issue.suggested_type,
                "lineno": issue.lineno,
                "description": issue.description,
                "suggestion": issue.suggestion,
            }
            for issue in func.data_structure.issues
        ]

    # Loop analysis
    if func.complexity.loop_analysis:
        la = func.complexity.loop_analysis
        result["loops"] = {
            "total": la.total_loops,
            "max_depth": la.max_depth,
            "details": [
                {
                    "kind": l.kind.value,
                    "lineno": l.lineno,
                    "depth": l.depth,
                    "has_invariant_code": l.has_invariant_code,
                    "has_expensive_operation": l.has_expensive_operation,
                }
                for l in la.loops
            ],
        }

    # Recursion
    if func.complexity.recursion_info and func.complexity.recursion_info.is_recursive:
        ri = func.complexity.recursion_info
        result["recursion"] = {
            "is_recursive": True,
            "direct_calls": ri.direct_calls,
            "has_base_case": ri.has_base_case,
            "estimated_branches": ri.estimated_branches,
            "is_tail_recursive": ri.is_tail_recursive,
            "can_be_memoized": ri.can_be_memoized,
            "depth_pattern": ri.depth_pattern,
        }

    return result


def _serialize_file(file_report: FileReport) -> dict:
    """Serialize a FileReport to a dict."""
    result = {
        "filepath": str(file_report.filepath),
        "line_count": file_report.line_count,
        "worst_complexity": file_report.worst_complexity.value,
        "total_functions": file_report.total_functions,
        "total_issues": file_report.total_issues,
        "functions": [
            _serialize_function(f)
            for f in file_report.functions_by_complexity
        ],
    }

    if file_report.dead_code and file_report.dead_code.total > 0:
        result["dead_code"] = [
            {
                "kind": item.kind,
                "lineno": item.lineno,
                "name": item.name,
                "description": item.description,
            }
            for item in file_report.dead_code.items
        ]

    if file_report.parse_errors:
        result["parse_errors"] = file_report.parse_errors

    return result


def render_json(report: AnalysisReport) -> str:
    """Render an analysis report as a JSON string.

    Args:
        report: The analysis report.

    Returns:
        JSON string with full analysis data.
    """
    data = {
        "fiopt_version": report.fiopt_version,
        "timestamp": report.timestamp,
        "analysis_duration_ms": round(report.analysis_duration_ms, 2),
        "summary": {
            "total_files": report.total_files,
            "total_functions": report.total_functions,
            "total_lines": report.total_lines,
            "worst_complexity": report.worst_complexity.value,
            "total_issues": report.total_issues,
        },
        "bottlenecks": report.bottlenecks,
        "suggestions": report.suggestions,
        "files": [_serialize_file(f) for f in report.files],
    }

    return json.dumps(data, indent=2, ensure_ascii=False)


def save_json_report(report: AnalysisReport, output_path: str | Path) -> Path:
    """Generate and save a JSON report.

    Args:
        report: The analysis report.
        output_path: Where to save the JSON file.

    Returns:
        Path to the saved file.
    """
    path = Path(output_path)
    content = render_json(report)
    path.write_text(content, encoding="utf-8")
    return path
