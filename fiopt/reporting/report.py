"""Analysis report data model.

Central data structure that aggregates all analysis results
for a single file or project into a unified report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from fiopt.config import ComplexityClass, Severity
from fiopt.analyzer.complexity_estimator import ComplexityResult
from fiopt.analyzer.pattern_matcher import PatternAnalysis
from fiopt.analyzer.dead_code_detector import DeadCodeAnalysis
from fiopt.analyzer.data_structure_analyzer import DataStructureAnalysis


@dataclass
class FunctionReport:
    """Analysis report for a single function."""
    name: str
    lineno: int
    end_lineno: int
    line_count: int
    # Complexity
    complexity: ComplexityResult
    # Anti-patterns
    patterns: PatternAnalysis | None = None
    # Data structure issues
    data_structure: DataStructureAnalysis | None = None
    # Severity (derived from complexity + issues)
    severity: Severity = Severity.INFO

    @property
    def total_issues(self) -> int:
        count = 0
        if self.patterns:
            count += len(self.patterns.anti_patterns)
        if self.data_structure:
            count += len(self.data_structure.issues)
        count += len(self.complexity.warnings)
        return count

    @property
    def summary_line(self) -> str:
        return (
            f"{self.name} (L{self.lineno}-{self.end_lineno}): "
            f"{self.complexity.estimated_complexity.value} | "
            f"{self.total_issues} issue(s)"
        )


@dataclass
class FileReport:
    """Analysis report for a single file."""
    filepath: Path
    line_count: int
    function_reports: list[FunctionReport] = field(default_factory=list)
    dead_code: DeadCodeAnalysis | None = None
    # Aggregate stats
    parse_errors: list[str] = field(default_factory=list)

    @property
    def worst_complexity(self) -> ComplexityClass:
        if not self.function_reports:
            return ComplexityClass.O_1
        return max(f.complexity.estimated_complexity for f in self.function_reports)

    @property
    def total_functions(self) -> int:
        return len(self.function_reports)

    @property
    def total_issues(self) -> int:
        count = sum(f.total_issues for f in self.function_reports)
        if self.dead_code:
            count += self.dead_code.total
        return count

    @property
    def critical_functions(self) -> list[FunctionReport]:
        """Functions with critical severity."""
        return [f for f in self.function_reports if f.severity == Severity.CRITICAL]

    @property
    def functions_by_complexity(self) -> list[FunctionReport]:
        """Functions sorted by complexity (worst first)."""
        return sorted(
            self.function_reports,
            key=lambda f: f.complexity.estimated_complexity.rank,
            reverse=True,
        )


@dataclass
class AnalysisReport:
    """Complete analysis report — the top-level output of FiOpt."""
    files: list[FileReport] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    analysis_duration_ms: float = 0.0
    fiopt_version: str = "0.1.0"

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_functions(self) -> int:
        return sum(f.total_functions for f in self.files)

    @property
    def total_lines(self) -> int:
        return sum(f.line_count for f in self.files)

    @property
    def total_issues(self) -> int:
        return sum(f.total_issues for f in self.files)

    @property
    def worst_complexity(self) -> ComplexityClass:
        if not self.files:
            return ComplexityClass.O_1
        return max(f.worst_complexity for f in self.files)

    @property
    def complexity(self) -> str:
        """Overall worst-case complexity as a string."""
        return self.worst_complexity.value

    @property
    def bottlenecks(self) -> list[str]:
        """List of human-readable bottleneck descriptions."""
        bottlenecks = []
        for file_report in self.files:
            for func in file_report.functions_by_complexity:
                if func.complexity.estimated_complexity >= ComplexityClass.O_N_SQUARED:
                    bottlenecks.append(
                        f"{file_report.filepath.name}:{func.name} "
                        f"(L{func.lineno}) — {func.complexity.estimated_complexity.value}"
                        + (f": {func.complexity.bottleneck_description}"
                           if func.complexity.bottleneck_description else "")
                    )
        return bottlenecks

    @property
    def suggestions(self) -> list[str]:
        """List of optimization suggestions."""
        suggestions = []
        for file_report in self.files:
            for func in file_report.function_reports:
                # From complexity warnings
                for warning in func.complexity.warnings:
                    suggestions.append(warning)
                # From anti-patterns
                if func.patterns:
                    for pattern in func.patterns.anti_patterns:
                        suggestions.append(
                            f"{file_report.filepath.name}:{func.name} (L{pattern.lineno}): "
                            f"{pattern.suggestion}"
                        )
                # From data structure issues
                if func.data_structure:
                    for issue in func.data_structure.issues:
                        suggestions.append(
                            f"{file_report.filepath.name}:{func.name} (L{issue.lineno}): "
                            f"{issue.suggestion}"
                        )
        return suggestions

    @property
    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"FiOpt Analysis Report",
            f"{'=' * 50}",
            f"Files analyzed: {self.total_files}",
            f"Functions analyzed: {self.total_functions}",
            f"Total lines: {self.total_lines}",
            f"Worst complexity: {self.worst_complexity.value}",
            f"Total issues: {self.total_issues}",
        ]
        if self.bottlenecks:
            lines.append(f"\nBottlenecks:")
            for b in self.bottlenecks[:5]:
                lines.append(f"  • {b}")
        if self.suggestions:
            lines.append(f"\nSuggestions:")
            for s in self.suggestions[:5]:
                lines.append(f"  • {s}")
        return "\n".join(lines)
