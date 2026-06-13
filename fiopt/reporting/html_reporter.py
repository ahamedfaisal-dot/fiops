"""HTML report generation for FiOpt analysis.

Generates a standalone, beautiful HTML report with:
- Embedded CSS (no external dependencies)
- Function complexity breakdown
- Issue highlights with suggestions
- Summary statistics
- Dark-mode design
"""

from __future__ import annotations

from pathlib import Path

from fiopt.config import ComplexityClass, Severity
from fiopt.reporting.report import AnalysisReport, FileReport, FunctionReport


_COMPLEXITY_COLORS = {
    ComplexityClass.O_1: "#22c55e",
    ComplexityClass.O_LOG_N: "#22c55e",
    ComplexityClass.O_N: "#06b6d4",
    ComplexityClass.O_N_LOG_N: "#06b6d4",
    ComplexityClass.O_N_SQUARED: "#eab308",
    ComplexityClass.O_N_CUBED: "#ef4444",
    ComplexityClass.O_N_K: "#ef4444",
    ComplexityClass.O_2_N: "#dc2626",
    ComplexityClass.O_N_FACTORIAL: "#dc2626",
    ComplexityClass.UNKNOWN: "#6b7280",
}

_SEVERITY_COLORS = {
    Severity.INFO: "#3b82f6",
    Severity.WARNING: "#eab308",
    Severity.CRITICAL: "#ef4444",
}

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FiOpt Analysis Report</title>
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border: #334155;
            --accent: #06b6d4;
            --accent-glow: rgba(6, 182, 212, 0.15);
            --green: #22c55e;
            --yellow: #eab308;
            --red: #ef4444;
            --blue: #3b82f6;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}

        /* Header */
        .header {{
            text-align: center;
            padding: 3rem 0 2rem;
            border-bottom: 1px solid var(--border);
            margin-bottom: 2rem;
        }}

        .header h1 {{
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent), #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }}

        .header .tagline {{
            color: var(--text-secondary);
            font-size: 1.1rem;
        }}

        .header .meta {{
            color: var(--text-muted);
            font-size: 0.85rem;
            margin-top: 1rem;
        }}

        /* Summary Cards */
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .summary-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            transition: transform 0.2s, border-color 0.2s;
        }}

        .summary-card:hover {{
            transform: translateY(-2px);
            border-color: var(--accent);
        }}

        .summary-card .value {{
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }}

        .summary-card .label {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        /* File Section */
        .file-section {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 1.5rem;
            overflow: hidden;
        }}

        .file-header {{
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .file-header h2 {{
            font-size: 1.1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .file-header .stats {{
            color: var(--text-muted);
            font-size: 0.85rem;
        }}

        /* Function Table */
        .func-table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .func-table th {{
            background: rgba(6, 182, 212, 0.08);
            padding: 0.75rem 1rem;
            text-align: left;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border);
        }}

        .func-table td {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid rgba(51, 65, 85, 0.5);
            font-size: 0.9rem;
        }}

        .func-table tr:hover td {{
            background: var(--bg-card-hover);
        }}

        .func-table tr:last-child td {{
            border-bottom: none;
        }}

        .complexity-badge {{
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.85rem;
            font-family: 'Consolas', 'Monaco', monospace;
        }}

        .severity-badge {{
            display: inline-block;
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        /* Issues */
        .issues-section {{
            padding: 1rem 1.5rem;
            border-top: 1px solid var(--border);
        }}

        .issues-section h3 {{
            font-size: 0.95rem;
            margin-bottom: 0.75rem;
            color: var(--yellow);
        }}

        .issue {{
            background: rgba(234, 179, 8, 0.05);
            border-left: 3px solid var(--yellow);
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            border-radius: 0 6px 6px 0;
        }}

        .issue.critical {{
            background: rgba(239, 68, 68, 0.05);
            border-left-color: var(--red);
        }}

        .issue.info {{
            background: rgba(59, 130, 246, 0.05);
            border-left-color: var(--blue);
        }}

        .issue .title {{
            font-weight: 600;
            font-size: 0.9rem;
        }}

        .issue .description {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 0.25rem;
        }}

        .issue .suggestion {{
            color: var(--green);
            font-size: 0.85rem;
            margin-top: 0.25rem;
        }}

        /* Bottlenecks */
        .bottleneck-section {{
            background: rgba(239, 68, 68, 0.05);
            border: 1px solid rgba(239, 68, 68, 0.2);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }}

        .bottleneck-section h3 {{
            color: var(--red);
            margin-bottom: 0.75rem;
        }}

        .bottleneck-item {{
            padding: 0.5rem 0;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 2rem 0;
            color: var(--text-muted);
            font-size: 0.8rem;
            border-top: 1px solid var(--border);
            margin-top: 2rem;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}
            .header h1 {{
                font-size: 1.8rem;
            }}
            .summary-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>FiOpt</h1>
            <div class="tagline">AI-Powered Code Complexity &amp; Optimization Engine</div>
            <div class="meta">Generated: {timestamp} | Duration: {duration}ms | v{version}</div>
        </div>

        <div class="summary-grid">
            <div class="summary-card">
                <div class="value">{total_files}</div>
                <div class="label">Files</div>
            </div>
            <div class="summary-card">
                <div class="value">{total_functions}</div>
                <div class="label">Functions</div>
            </div>
            <div class="summary-card">
                <div class="value">{total_lines}</div>
                <div class="label">Lines</div>
            </div>
            <div class="summary-card">
                <div class="value" style="color: {worst_color}">{worst_complexity}</div>
                <div class="label">Worst Complexity</div>
            </div>
            <div class="summary-card">
                <div class="value" style="color: {issues_color}">{total_issues}</div>
                <div class="label">Issues</div>
            </div>
        </div>

        {bottleneck_html}

        {files_html}

        <div class="footer">
            FiOpt — "Analyze. Detect. Accelerate." — v{version}
        </div>
    </div>
</body>
</html>
"""


def _get_complexity_color(c: ComplexityClass) -> str:
    return _COMPLEXITY_COLORS.get(c, "#6b7280")


def _get_severity_color(s: Severity) -> str:
    return _SEVERITY_COLORS.get(s, "#6b7280")


def _render_function_row(func: FunctionReport) -> str:
    c = func.complexity.estimated_complexity
    c_color = _get_complexity_color(c)
    s_color = _get_severity_color(func.severity)

    return f"""\
        <tr>
            <td><strong>{func.name}</strong></td>
            <td>L{func.lineno}–{func.end_lineno}</td>
            <td>
                <span class="complexity-badge"
                      style="background: {c_color}22; color: {c_color};">
                    {c.value}
                </span>
            </td>
            <td>{func.complexity.confidence:.0%}</td>
            <td>{func.total_issues}</td>
            <td>
                <span class="severity-badge"
                      style="background: {s_color}22; color: {s_color};">
                    {func.severity.value.upper()}
                </span>
            </td>
        </tr>"""


def _render_issues_html(file_report: FileReport) -> str:
    issues_parts = []

    for func in file_report.function_reports:
        if func.patterns:
            for p in func.patterns.anti_patterns:
                css_class = p.severity.value
                issues_parts.append(f"""\
                <div class="issue {css_class}">
                    <div class="title">{func.name} (L{p.lineno}): {p.name}</div>
                    <div class="description">{p.description}</div>
                    <div class="suggestion">→ {p.suggestion}</div>
                </div>""")

        if func.data_structure:
            for issue in func.data_structure.issues:
                issues_parts.append(f"""\
                <div class="issue warning">
                    <div class="title">{func.name} (L{issue.lineno}): {issue.current_type} → {issue.suggested_type}</div>
                    <div class="description">{issue.description}</div>
                    <div class="suggestion">→ {issue.suggestion}</div>
                </div>""")

        for warning in func.complexity.warnings:
            issues_parts.append(f"""\
                <div class="issue warning">
                    <div class="description">{warning}</div>
                </div>""")

    if not issues_parts:
        return ""

    return f"""\
        <div class="issues-section">
            <h3>Issues &amp; Suggestions</h3>
            {"".join(issues_parts)}
        </div>"""


def _render_file_section(file_report: FileReport) -> str:
    rows = "".join(
        _render_function_row(func)
        for func in file_report.functions_by_complexity
    )

    issues_html = _render_issues_html(file_report)

    return f"""\
    <div class="file-section">
        <div class="file-header">
            <h2>{file_report.filepath.name}</h2>
            <span class="stats">{file_report.line_count} lines · {file_report.total_functions} functions</span>
        </div>
        <table class="func-table">
            <thead>
                <tr>
                    <th>Function</th>
                    <th>Lines</th>
                    <th>Complexity</th>
                    <th>Confidence</th>
                    <th>Issues</th>
                    <th>Severity</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        {issues_html}
    </div>"""


def render_html(report: AnalysisReport) -> str:
    """Render an analysis report as a standalone HTML string.

    Args:
        report: The analysis report to render.

    Returns:
        Complete HTML string.
    """
    # Files
    files_html = "\n".join(
        _render_file_section(f) for f in report.files
    )

    # Bottlenecks
    bottleneck_html = ""
    if report.bottlenecks:
        items = "\n".join(
            f'<div class="bottleneck-item">{b}</div>'
            for b in report.bottlenecks[:10]
        )
        bottleneck_html = f"""\
        <div class="bottleneck-section">
            <h3>Performance Bottlenecks</h3>
            {items}
        </div>"""

    worst = report.worst_complexity
    worst_color = _get_complexity_color(worst)
    issues_color = "#ef4444" if report.total_issues > 0 else "#22c55e"

    return _HTML_TEMPLATE.format(
        timestamp=report.timestamp,
        duration=f"{report.analysis_duration_ms:.1f}",
        version=report.fiopt_version,
        total_files=report.total_files,
        total_functions=report.total_functions,
        total_lines=report.total_lines,
        worst_complexity=worst.value,
        worst_color=worst_color,
        total_issues=report.total_issues,
        issues_color=issues_color,
        bottleneck_html=bottleneck_html,
        files_html=files_html,
    )


def save_html_report(report: AnalysisReport, output_path: str | Path) -> Path:
    """Generate and save an HTML report.

    Args:
        report: The analysis report.
        output_path: Where to save the HTML file.

    Returns:
        Path to the saved file.
    """
    path = Path(output_path)
    html = render_html(report)
    path.write_text(html, encoding="utf-8")
    return path
