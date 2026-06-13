"""Recursion detection and analysis.

Detects:
- Direct recursion (function calls itself)
- Mutual recursion (A calls B calls A)
- Missing memoization opportunities
- Tail recursion candidates
- Recursion depth estimation from base cases
- Overlapping subproblems (dynamic programming opportunities)
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass
class RecursionInfo:
    """Information about recursion in a function."""
    function_name: str
    lineno: int
    end_lineno: int
    is_recursive: bool = False
    # Direct recursion: function calls itself
    direct_calls: list[int] = field(default_factory=list)  # line numbers of recursive calls
    # Mutual recursion: calls a function that calls back
    mutual_calls: dict[str, list[int]] = field(default_factory=dict)
    # Analysis
    has_base_case: bool = False
    base_case_lines: list[int] = field(default_factory=list)
    estimated_branches: int = 1  # how many recursive calls per invocation
    is_tail_recursive: bool = False
    tail_recursive_lines: list[int] = field(default_factory=list)
    can_be_memoized: bool = False
    memoization_reason: str = ""
    has_overlapping_subproblems: bool = False
    # Depth estimation
    depth_pattern: str = ""  # e.g., "linear", "logarithmic", "exponential"

    @property
    def total_recursive_calls(self) -> int:
        return len(self.direct_calls) + sum(len(v) for v in self.mutual_calls.values())


class _RecursionVisitor(ast.NodeVisitor):
    """Detect recursion patterns in a function."""

    def __init__(self, func_name: str, all_function_names: set[str]) -> None:
        self.func_name = func_name
        self.all_function_names = all_function_names
        self.direct_calls: list[int] = []
        self.other_function_calls: dict[str, list[int]] = {}
        self.has_base_case = False
        self.base_case_lines: list[int] = []
        self.is_tail_recursive = False
        self.tail_recursive_lines: list[int] = []
        self.branches_per_call = 0
        self._in_return = False
        self._return_is_just_call = False
        # Track if args are modified (for memoization analysis)
        self._args: set[str] = set()
        self._args_used_in_recursive_calls = False
        self._recursive_call_args: list[list[ast.expr]] = []
        self._func_node: ast.AST | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Don't descend into nested function definitions
        if node.name != self.func_name:
            return
        self._args = {a.arg for a in node.args.args}
        self._func_node = node
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_If(self, node: ast.If) -> None:
        """Check for base cases — if branches that return without recursing."""
        # A base case is typically a simple condition that returns a constant
        # or does not contain a recursive call.
        for branch_body in [node.body, node.orelse]:
            if not branch_body:
                continue
            has_recursive = False
            has_return = False
            for stmt in branch_body:
                for child in ast.walk(stmt):
                    if isinstance(child, ast.Call) and self._is_self_call(child):
                        has_recursive = True
                    if isinstance(child, ast.Return):
                        has_return = True

            if has_return and not has_recursive:
                self.has_base_case = True
                self.base_case_lines.append(node.lineno)

        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        """Check for tail recursion — return f(args) with no other work."""
        if node.value and isinstance(node.value, ast.Call):
            if self._is_self_call(node.value):
                self.is_tail_recursive = True
                self.tail_recursive_lines.append(node.lineno)
        # Check for return expr + f(args) pattern (NOT tail recursive)
        elif node.value and isinstance(node.value, ast.BinOp):
            # e.g., return n * factorial(n-1) — not tail recursive
            pass

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Track all function calls."""
        call_name = self._get_call_name(node)

        if call_name == self.func_name:
            self.direct_calls.append(node.lineno)
            self._recursive_call_args.append(node.args)
        elif call_name in self.all_function_names:
            if call_name not in self.other_function_calls:
                self.other_function_calls[call_name] = []
            self.other_function_calls[call_name].append(node.lineno)

        self.generic_visit(node)

    def _is_self_call(self, node: ast.Call) -> bool:
        return self._get_call_name(node) == self.func_name

    def _get_call_name(self, node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    def _count_recursive_calls_in_node(self, node: ast.AST) -> int:
        """Count direct recursive calls within a single AST node (non-recursive into sub-ifs)."""
        count = 0
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Call) and self._is_self_call(child):
                count += 1
            elif not isinstance(child, ast.If):
                count += self._count_recursive_calls_in_node(child)
        return count

    def _effective_branches_in_if(self, node: ast.If) -> int:
        """Determine effective branching factor in an if/elif/else chain.

        If every branch has at most 1 recursive call and no branch
        accumulates calls alongside others (i.e. they are mutually exclusive),
        the effective branching is the max per-branch, not the sum.
        """
        branch_counts: list[int] = []

        # Count in the `if` body
        count = 0
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                count += self._effective_branches_in_if(stmt)
            else:
                count += self._count_recursive_calls_in_node(stmt)
        branch_counts.append(count)

        # Count in the `else` body (which may be another elif — an ast.If)
        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                # elif chain — recurse
                branch_counts.append(self._effective_branches_in_if(node.orelse[0]))
            else:
                count = 0
                for stmt in node.orelse:
                    if isinstance(stmt, ast.If):
                        count += self._effective_branches_in_if(stmt)
                    else:
                        count += self._count_recursive_calls_in_node(stmt)
                branch_counts.append(count)

        # If every branch has at most 1 recursive call, the branches are
        # mutually exclusive so the effective branching factor is the max.
        if all(c <= 1 for c in branch_counts):
            return max(branch_counts) if branch_counts else 0

        # Otherwise, be conservative: return the maximum branch count
        return max(branch_counts) if branch_counts else 0

    @property
    def _effective_branches(self) -> int:
        """Effective branching factor, accounting for mutually exclusive branches."""
        if self._func_node is None:
            return len(self.direct_calls)
        return self._compute_effective_branches(self._func_node)

    def _compute_effective_branches(self, func_node: ast.AST) -> int:
        """Compute the effective branching factor for the function body.

        Walks the top-level statements.  Recursive calls in mutually-exclusive
        if/elif/else branches count as 1 branch, not N.
        """
        total = 0
        for stmt in ast.iter_child_nodes(func_node):
            if isinstance(stmt, ast.If):
                total += self._effective_branches_in_if(stmt)
            elif isinstance(stmt, ast.Call) and self._is_self_call(stmt):
                total += 1
            else:
                total += self._count_recursive_calls_in_node(stmt)
        return max(total, 1) if self.direct_calls else 0

    def analyze_recursive_pattern(self) -> tuple[int, str, bool]:
        """Analyze the recursion pattern.

        Returns:
            (branches_per_call, depth_pattern, has_overlapping_subproblems)
        """
        if not self.direct_calls:
            return (0, "", False)

        # Use effective branching: calls in mutually-exclusive if/elif/else
        # count as 1 branch, not N.
        branches = self._effective_branches
        has_overlapping = False
        depth_pattern = "linear"

        if branches >= 2:
            depth_pattern = "exponential"
            # Check for overlapping subproblems (fibonacci-like)
            # If multiple recursive calls with different but overlapping args
            if len(self._recursive_call_args) >= 2:
                has_overlapping = True

        # Collect variables computed via floor division (e.g., mid = (x+y)//2)
        halved_vars: set[str] = set()
        if self._func_node is not None:
            for stmt in ast.walk(self._func_node):
                if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.BinOp):
                    if isinstance(stmt.value.op, ast.FloorDiv):
                        for target in stmt.targets:
                            if isinstance(target, ast.Name):
                                halved_vars.add(target.id)

        # Check if args are halved (binary search / divide and conquer)
        for args in self._recursive_call_args:
            for arg in args:
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.FloorDiv):
                    depth_pattern = "logarithmic"
                    break
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, (ast.Sub, ast.Add)):
                    # Check if operand references a halved variable (e.g. mid + 1)
                    operands = [arg.left, arg.right]
                    if any(
                        isinstance(op, ast.Name) and op.id in halved_vars
                        for op in operands
                    ):
                        depth_pattern = "logarithmic"
                        break
                    if depth_pattern != "logarithmic":
                        depth_pattern = "linear"
                if isinstance(arg, ast.Name) and arg.id in halved_vars:
                    depth_pattern = "logarithmic"
                    break
                if isinstance(arg, ast.Subscript):
                    # arr[mid:] or arr[:mid] — likely divide and conquer
                    if isinstance(arg.slice, ast.Slice):
                        depth_pattern = "logarithmic"

        return (branches, depth_pattern, has_overlapping)


def detect_recursion(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    all_function_names: set[str] | None = None,
    all_functions: dict[str, ast.FunctionDef] | None = None,
) -> RecursionInfo:
    """Detect and analyze recursion in a function.

    Args:
        func_node: The function to analyze.
        all_function_names: Names of all functions in the module (for mutual recursion).
        all_functions: Map of function name to AST node (for mutual recursion analysis).

    Returns:
        RecursionInfo with detailed recursion analysis.
    """
    if all_function_names is None:
        all_function_names = set()

    func_name = func_node.name
    visitor = _RecursionVisitor(func_name, all_function_names)
    visitor.visit(func_node)

    info = RecursionInfo(
        function_name=func_name,
        lineno=func_node.lineno,
        end_lineno=func_node.end_lineno or func_node.lineno,
        is_recursive=len(visitor.direct_calls) > 0,
        direct_calls=visitor.direct_calls,
        has_base_case=visitor.has_base_case,
        base_case_lines=visitor.base_case_lines,
        is_tail_recursive=visitor.is_tail_recursive,
        tail_recursive_lines=visitor.tail_recursive_lines,
    )

    if info.is_recursive:
        branches, depth_pattern, has_overlapping = visitor.analyze_recursive_pattern()
        info.estimated_branches = branches
        info.depth_pattern = depth_pattern
        info.has_overlapping_subproblems = has_overlapping

        # Determine if memoization would help
        if has_overlapping or branches >= 2:
            info.can_be_memoized = True
            if has_overlapping:
                info.memoization_reason = (
                    "Function has overlapping subproblems — "
                    "memoization can reduce exponential to polynomial complexity."
                )
            else:
                info.memoization_reason = (
                    "Function makes multiple recursive calls — "
                    "memoization can avoid redundant computation."
                )

    # Detect mutual recursion
    if all_functions:
        for called_name, call_lines in visitor.other_function_calls.items():
            if called_name in all_functions:
                # Check if the called function calls back to us
                other_visitor = _RecursionVisitor(called_name, all_function_names)
                other_visitor.visit(all_functions[called_name])
                if func_name in other_visitor.other_function_calls:
                    info.mutual_calls[called_name] = call_lines
                    info.is_recursive = True

    return info
