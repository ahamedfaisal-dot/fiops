"""Data structure usage analysis.

Detects:
- List used where set would be faster (membership checks)
- Dict used where defaultdict would be cleaner
- Repeated dict key lookups that should be cached
- List used as a stack/queue (should use collections.deque)
- Inefficient data structure for the access pattern
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass
class DataStructureIssue:
    """A detected data structure misuse."""
    variable_name: str
    current_type: str
    suggested_type: str
    lineno: int
    description: str
    suggestion: str
    estimated_impact: str


@dataclass
class DataStructureAnalysis:
    """Data structure analysis results for a function."""
    function_name: str
    issues: list[DataStructureIssue] = field(default_factory=list)


class _DataStructureVisitor(ast.NodeVisitor):
    """Analyze data structure usage patterns."""

    def __init__(self) -> None:
        self.issues: list[DataStructureIssue] = []
        # Track how variables are used
        self._list_vars: dict[str, int] = {}    # name -> definition line
        self._dict_vars: dict[str, int] = {}
        self._membership_checks: dict[str, list[int]] = {}  # name -> check lines
        self._list_pops_at_zero: dict[str, list[int]] = {}  # list.pop(0) usage
        self._dict_key_checks: dict[str, list[int]] = {}    # `if key in dict` lines
        self._dict_setdefault_candidates: dict[str, list[int]] = {}

    def visit_Assign(self, node: ast.Assign) -> None:
        """Track variable type assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                if isinstance(node.value, ast.List):
                    self._list_vars[name] = node.lineno
                elif isinstance(node.value, ast.Dict):
                    self._dict_vars[name] = node.lineno
                elif isinstance(node.value, ast.Call):
                    func_name = self._get_call_name(node.value)
                    if func_name == "list":
                        self._list_vars[name] = node.lineno
                    elif func_name == "dict":
                        self._dict_vars[name] = node.lineno

        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        """Track membership checks."""
        for i, op in enumerate(node.ops):
            if isinstance(op, (ast.In, ast.NotIn)):
                comparator = node.comparators[i]
                if isinstance(comparator, ast.Name):
                    name = comparator.id
                    if name not in self._membership_checks:
                        self._membership_checks[name] = []
                    self._membership_checks[name].append(node.lineno)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Track method calls on data structures."""
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                var_name = node.func.value.id
                method = node.func.attr

                # Detect list.pop(0) — should use collections.deque
                if method == "pop" and var_name in self._list_vars:
                    if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 0:
                        if var_name not in self._list_pops_at_zero:
                            self._list_pops_at_zero[var_name] = []
                        self._list_pops_at_zero[var_name].append(node.lineno)

                # Detect list.insert(0, x) — should use collections.deque
                if method == "insert" and var_name in self._list_vars:
                    if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 0:
                        if var_name not in self._list_pops_at_zero:
                            self._list_pops_at_zero[var_name] = []
                        self._list_pops_at_zero[var_name].append(node.lineno)

        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        """Detect dict key check + assignment pattern (should use setdefault)."""
        # Pattern: if key not in d: d[key] = value
        if isinstance(node.test, ast.Compare):
            for i, op in enumerate(node.test.ops):
                if isinstance(op, ast.NotIn):
                    comparator = node.test.comparators[i]
                    if isinstance(comparator, ast.Name) and comparator.id in self._dict_vars:
                        # Check if the body assigns to that dict
                        for stmt in node.body:
                            if isinstance(stmt, ast.Assign):
                                for target in stmt.targets:
                                    if (
                                        isinstance(target, ast.Subscript)
                                        and isinstance(target.value, ast.Name)
                                        and target.value.id == comparator.id
                                    ):
                                        name = comparator.id
                                        if name not in self._dict_setdefault_candidates:
                                            self._dict_setdefault_candidates[name] = []
                                        self._dict_setdefault_candidates[name].append(node.lineno)

        self.generic_visit(node)

    def finalize(self) -> list[DataStructureIssue]:
        """Generate issues based on accumulated analysis."""
        issues = []

        # Lists used for membership checks
        for var_name, check_lines in self._membership_checks.items():
            if var_name in self._list_vars and len(check_lines) >= 1:
                issues.append(DataStructureIssue(
                    variable_name=var_name,
                    current_type="list",
                    suggested_type="set",
                    lineno=self._list_vars[var_name],
                    description=(
                        f"List '{var_name}' is used for {len(check_lines)} membership check(s) "
                        f"at line(s) {', '.join(str(l) for l in check_lines)} — "
                        f"each check is O(n)"
                    ),
                    suggestion=(
                        f"Convert '{var_name}' to a set for O(1) lookups: "
                        f"{var_name} = set({var_name})"
                    ),
                    estimated_impact="O(n) → O(1) per membership check",
                ))

        # Lists used as queues (pop(0) / insert(0, x))
        for var_name, lines in self._list_pops_at_zero.items():
            issues.append(DataStructureIssue(
                variable_name=var_name,
                current_type="list",
                suggested_type="collections.deque",
                lineno=self._list_vars.get(var_name, lines[0]),
                description=(
                    f"List '{var_name}' uses pop(0)/insert(0, x) at line(s) "
                    f"{', '.join(str(l) for l in lines)} — "
                    f"O(n) operation on list (shifts all elements)"
                ),
                suggestion=(
                    f"Use collections.deque for O(1) popleft()/appendleft(): "
                    f"from collections import deque; {var_name} = deque({var_name})"
                ),
                estimated_impact="O(n) → O(1) per pop/insert at index 0",
            ))

        # Dict key check + assign pattern
        for var_name, lines in self._dict_setdefault_candidates.items():
            issues.append(DataStructureIssue(
                variable_name=var_name,
                current_type="dict (manual key check)",
                suggested_type="dict.setdefault() or collections.defaultdict",
                lineno=lines[0],
                description=(
                    f"Dict '{var_name}' uses 'if key not in dict' pattern "
                    f"at line(s) {', '.join(str(l) for l in lines)}"
                ),
                suggestion=(
                    f"Use {var_name}.setdefault(key, default) or "
                    f"collections.defaultdict for cleaner code."
                ),
                estimated_impact="Cleaner code, slight performance improvement",
            ))

        return issues

    def _get_call_name(self, node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""


def detect_data_structure_issues(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> DataStructureAnalysis:
    """Detect data structure misuse in a function.

    Checks for:
    - Lists used where sets would be faster
    - Lists used as queues (pop(0))
    - Dict key-check-then-assign patterns

    Args:
        func_node: The function to analyze.

    Returns:
        DataStructureAnalysis with detected issues.
    """
    visitor = _DataStructureVisitor()
    visitor.visit(func_node)
    issues = visitor.finalize()

    return DataStructureAnalysis(
        function_name=func_node.name,
        issues=issues,
    )
