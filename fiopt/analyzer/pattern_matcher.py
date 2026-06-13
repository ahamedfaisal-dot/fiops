"""Algorithmic anti-pattern detection.

Detects common performance anti-patterns:
- `in` check on lists (should use sets)
- String concatenation in loops
- Repeated dict lookups without caching
- Sorting inside loops
- Repeated computation
- Unnecessary list creation when generator suffices
- Inefficient membership testing
- Repeated I/O in loops
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum


class PatternSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class PatternCategory(Enum):
    DATA_STRUCTURE = "data_structure"
    STRING_OPERATION = "string_operation"
    ALGORITHM = "algorithm"
    IO_OPERATION = "io_operation"
    MEMORY = "memory"
    COMPUTATION = "computation"


@dataclass
class AntiPattern:
    """A detected anti-pattern."""
    name: str
    category: PatternCategory
    severity: PatternSeverity
    lineno: int
    end_lineno: int
    description: str
    suggestion: str
    estimated_impact: str  # e.g., "O(n) → O(1)"
    code_snippet: str = ""


@dataclass
class PatternAnalysis:
    """Results of anti-pattern detection for a function."""
    function_name: str
    anti_patterns: list[AntiPattern] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for p in self.anti_patterns if p.severity == PatternSeverity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for p in self.anti_patterns if p.severity == PatternSeverity.WARNING)


class _PatternVisitor(ast.NodeVisitor):
    """AST visitor that detects anti-patterns."""

    def __init__(self) -> None:
        self.patterns: list[AntiPattern] = []
        self._loop_depth = 0
        self._in_loop = False
        # Track variable types based on assignments
        self._list_vars: set[str] = set()
        self._set_vars: set[str] = set()
        self._dict_vars: set[str] = set()
        self._string_vars: set[str] = set()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Track variable types from assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                if isinstance(node.value, ast.List):
                    self._list_vars.add(name)
                elif isinstance(node.value, ast.Set):
                    self._set_vars.add(name)
                elif isinstance(node.value, ast.Dict):
                    self._dict_vars.add(name)
                elif isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    self._string_vars.add(name)
                elif isinstance(node.value, ast.Call):
                    func_name = self._get_call_name(node.value)
                    if func_name == "list":
                        self._list_vars.add(name)
                    elif func_name == "set":
                        self._set_vars.add(name)
                    elif func_name == "dict":
                        self._dict_vars.add(name)
                elif isinstance(node.value, ast.JoinedStr):
                    self._string_vars.add(name)

        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._loop_depth += 1
        self._in_loop = True
        self._check_loop_body(node)
        self.generic_visit(node)
        self._loop_depth -= 1
        if self._loop_depth == 0:
            self._in_loop = False

    def visit_While(self, node: ast.While) -> None:
        self._loop_depth += 1
        self._in_loop = True
        self._check_loop_body_while(node)
        self.generic_visit(node)
        self._loop_depth -= 1
        if self._loop_depth == 0:
            self._in_loop = False

    def visit_Compare(self, node: ast.Compare) -> None:
        """Detect `x in list_variable` (should be set)."""
        for i, op in enumerate(node.ops):
            if isinstance(op, (ast.In, ast.NotIn)):
                comparator = node.comparators[i]
                # Check if the comparator is a list literal
                if isinstance(comparator, ast.List) and len(comparator.elts) > 3:
                    self.patterns.append(AntiPattern(
                        name="list_membership_check",
                        category=PatternCategory.DATA_STRUCTURE,
                        severity=PatternSeverity.WARNING,
                        lineno=node.lineno,
                        end_lineno=node.end_lineno or node.lineno,
                        description=(
                            f"Membership check on list literal with {len(comparator.elts)} "
                            f"elements — O(n) per check"
                        ),
                        suggestion="Convert to a set literal for O(1) membership: {item1, item2, ...}",
                        estimated_impact="O(n) → O(1) per lookup",
                    ))
                # Check if it's a known list variable
                elif isinstance(comparator, ast.Name) and comparator.id in self._list_vars:
                    severity = PatternSeverity.CRITICAL if self._in_loop else PatternSeverity.WARNING
                    self.patterns.append(AntiPattern(
                        name="list_membership_check",
                        category=PatternCategory.DATA_STRUCTURE,
                        severity=severity,
                        lineno=node.lineno,
                        end_lineno=node.end_lineno or node.lineno,
                        description=(
                            f"Membership check `in {comparator.id}` on a list variable — O(n) per check"
                            + (" (inside loop!)" if self._in_loop else "")
                        ),
                        suggestion=(
                            f"Convert '{comparator.id}' to a set for O(1) lookups: "
                            f"{comparator.id} = set({comparator.id})"
                        ),
                        estimated_impact=(
                            "O(n²) → O(n)" if self._in_loop else "O(n) → O(1)"
                        ),
                    ))

        self.generic_visit(node)

    def _check_loop_body(self, node: ast.For) -> None:
        """Check for anti-patterns in a for loop body."""
        for stmt in node.body:
            self._check_string_concat_in_loop(stmt, node.lineno)
            self._check_sorting_in_loop(stmt, node.lineno)
            self._check_io_in_loop(stmt, node.lineno)
            self._check_list_extend_pattern(stmt, node.lineno)

    def _check_loop_body_while(self, node: ast.While) -> None:
        """Check for anti-patterns in a while loop body."""
        for stmt in node.body:
            self._check_string_concat_in_loop(stmt, node.lineno)
            self._check_sorting_in_loop(stmt, node.lineno)
            self._check_io_in_loop(stmt, node.lineno)

    def _check_string_concat_in_loop(self, stmt: ast.stmt, loop_line: int) -> None:
        """Detect string concatenation with += in a loop."""
        if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add):
            if isinstance(stmt.target, ast.Name):
                var_name = stmt.target.id
                # Check if we're concatenating strings
                if var_name in self._string_vars or (
                    isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str)
                ):
                    self.patterns.append(AntiPattern(
                        name="string_concat_in_loop",
                        category=PatternCategory.STRING_OPERATION,
                        severity=PatternSeverity.CRITICAL,
                        lineno=stmt.lineno,
                        end_lineno=stmt.end_lineno or stmt.lineno,
                        description=(
                            f"String concatenation with += in loop "
                            f"(line {stmt.lineno}) — creates new string each iteration O(n²)"
                        ),
                        suggestion=(
                            "Use a list to collect parts, then ''.join(parts) at the end. "
                            "Or use io.StringIO for building strings incrementally."
                        ),
                        estimated_impact="O(n²) → O(n)",
                    ))

    def _check_sorting_in_loop(self, stmt: ast.stmt, loop_line: int) -> None:
        """Detect sorting operations inside loops."""
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node)
                if call_name in ("sorted", "sort"):
                    self.patterns.append(AntiPattern(
                        name="sorting_in_loop",
                        category=PatternCategory.ALGORITHM,
                        severity=PatternSeverity.CRITICAL,
                        lineno=node.lineno,
                        end_lineno=node.end_lineno or node.lineno,
                        description=(
                            f"Sorting operation '{call_name}()' inside loop — "
                            f"O(n² log n) total"
                        ),
                        suggestion="Move sorting outside the loop if the data doesn't change, or use a sorted container.",
                        estimated_impact="O(n² log n) → O(n log n)",
                    ))

    def _check_io_in_loop(self, stmt: ast.stmt, loop_line: int) -> None:
        """Detect I/O operations inside loops."""
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node)
                if call_name in ("open", "read", "write", "readlines"):
                    self.patterns.append(AntiPattern(
                        name="io_in_loop",
                        category=PatternCategory.IO_OPERATION,
                        severity=PatternSeverity.WARNING,
                        lineno=node.lineno,
                        end_lineno=node.end_lineno or node.lineno,
                        description=f"I/O operation '{call_name}()' inside loop",
                        suggestion="Batch I/O operations outside the loop when possible.",
                        estimated_impact="Significant I/O overhead per iteration",
                    ))

    def _check_list_extend_pattern(self, stmt: ast.stmt, loop_line: int) -> None:
        """Detect using append in a loop where a comprehension would work."""
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
                if isinstance(call.func.value, ast.Name):
                    self.patterns.append(AntiPattern(
                        name="append_in_loop",
                        category=PatternCategory.MEMORY,
                        severity=PatternSeverity.INFO,
                        lineno=stmt.lineno,
                        end_lineno=stmt.end_lineno or stmt.lineno,
                        description=(
                            f"'{call.func.value.id}.append()' in loop — "
                            f"consider using a list comprehension"
                        ),
                        suggestion="Replace loop + append with a list comprehension for clarity and minor performance gain.",
                        estimated_impact="Minor: list comprehensions are ~10-30% faster",
                    ))

    def _get_call_name(self, node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""


def detect_patterns(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> PatternAnalysis:
    """Detect anti-patterns in a function.

    Scans for common performance anti-patterns like:
    - List membership checks (should be sets)
    - String concatenation in loops
    - Sorting inside loops
    - I/O inside loops
    - Append-in-loop (could be comprehension)

    Args:
        func_node: The function to analyze.

    Returns:
        PatternAnalysis with all detected anti-patterns.
    """
    visitor = _PatternVisitor()
    visitor.visit(func_node)

    return PatternAnalysis(
        function_name=func_node.name,
        anti_patterns=visitor.patterns,
    )
