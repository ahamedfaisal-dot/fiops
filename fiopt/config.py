"""FiOpt configuration management."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """Severity levels for analysis findings."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ReportFormat(Enum):
    """Supported output formats."""
    TERMINAL = "terminal"
    HTML = "html"
    JSON = "json"


class ComplexityClass(Enum):
    """Known algorithmic complexity classes, ordered from best to worst."""
    O_1 = "O(1)"
    O_LOG_N = "O(log n)"
    O_N = "O(n)"
    O_N_LOG_N = "O(n log n)"
    O_N_SQUARED = "O(n²)"
    O_N_CUBED = "O(n³)"
    O_N_K = "O(nᵏ)"       # polynomial, k > 3
    O_2_N = "O(2ⁿ)"
    O_N_FACTORIAL = "O(n!)"
    UNKNOWN = "Unknown"

    @property
    def rank(self) -> int:
        """Numeric rank for comparison. Higher = worse."""
        _ranks = {
            ComplexityClass.O_1: 0,
            ComplexityClass.O_LOG_N: 1,
            ComplexityClass.O_N: 2,
            ComplexityClass.O_N_LOG_N: 3,
            ComplexityClass.O_N_SQUARED: 4,
            ComplexityClass.O_N_CUBED: 5,
            ComplexityClass.O_N_K: 6,
            ComplexityClass.O_2_N: 7,
            ComplexityClass.O_N_FACTORIAL: 8,
            ComplexityClass.UNKNOWN: 9,
        }
        return _ranks[self]

    def __lt__(self, other: ComplexityClass) -> bool:
        return self.rank < other.rank

    def __le__(self, other: ComplexityClass) -> bool:
        return self.rank <= other.rank

    def __gt__(self, other: ComplexityClass) -> bool:
        return self.rank > other.rank

    def __ge__(self, other: ComplexityClass) -> bool:
        return self.rank >= other.rank


@dataclass
class AnalysisConfig:
    """Configuration for FiOpt analysis."""
    # Complexity threshold to flag as warning
    complexity_warning_threshold: ComplexityClass = ComplexityClass.O_N_SQUARED
    # Complexity threshold to flag as critical
    complexity_critical_threshold: ComplexityClass = ComplexityClass.O_N_CUBED
    # Maximum nesting depth before warning
    max_nesting_depth: int = 3
    # Detect dead code
    detect_dead_code: bool = True
    # Detect anti-patterns
    detect_anti_patterns: bool = True
    # Detect data structure misuse
    detect_data_structure_issues: bool = True
    # Detect recursion issues
    detect_recursion_issues: bool = True
    # Report format
    report_format: ReportFormat = ReportFormat.TERMINAL
    # Output path for reports
    output_path: str | None = None
    # Include source code snippets in reports
    include_source: bool = True
    # Verbose output
    verbose: bool = False
    # File extensions to analyze
    file_extensions: list[str] = field(default_factory=lambda: [".py"])
    # Directories to exclude
    exclude_dirs: list[str] = field(
        default_factory=lambda: [
            "__pycache__", ".git", ".venv", "venv", "node_modules",
            ".tox", ".eggs", "dist", "build", ".mypy_cache",
        ]
    )
