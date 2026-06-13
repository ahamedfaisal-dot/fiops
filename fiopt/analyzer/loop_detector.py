"""Loop detection and nesting analysis.

Detects:
- for loops, while loops, and comprehensions
- Nesting depth and hierarchy
- Loop variable dependencies
- Loop-invariant code (code that doesn't depend on loop variables)
- Unnecessary nested loops
- Iteration over computed results that could be cached
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum


class LoopKind(Enum):
    FOR = "for"
    WHILE = "while"
    LIST_COMP = "list_comprehension"
    SET_COMP = "set_comprehension"
    DICT_COMP = "dict_comprehension"
    GEN_EXPR = "generator_expression"


@dataclass
class LoopVariable:
    """Information about a loop iteration variable."""
    name: str
    lineno: int
    iterable: str       # what's being iterated (e.g., "range(n)", "data")
    iterable_node: ast.expr | None = None


@dataclass
class LoopDetail:
    """Detailed information about a single loop."""
    kind: LoopKind
    lineno: int
    end_lineno: int
    col_offset: int
    # Nesting info
    depth: int            # 1 = top-level loop, 2 = nested once, etc.
    parent: LoopDetail | None = None
    children: list[LoopDetail] = field(default_factory=list)
    # Loop variables
    variables: list[LoopVariable] = field(default_factory=list)
    # Body info
    body_line_count: int = 0
    contains_break: bool = False
    contains_continue: bool = False
    contains_return: bool = False
    # Analysis results
    has_invariant_code: bool = False
    invariant_lines: list[int] = field(default_factory=list)
    has_expensive_operation: bool = False
    expensive_operations: list[str] = field(default_factory=list)
    # Function calls inside the loop
    function_calls: list[str] = field(default_factory=list)
    # AST node
    node: ast.AST | None = None

    @property
    def is_nested(self) -> bool:
        return self.depth > 1

    @property
    def has_children(self) -> bool:
        return len(self.children) > 0

    @property
    def max_child_depth(self) -> int:
        if not self.children:
            return self.depth
        return max(c.max_child_depth for c in self.children)

    @property
    def total_depth(self) -> int:
        """Total nesting depth from this loop to its deepest child."""
        return self.max_child_depth - self.depth + 1


@dataclass
class LoopAnalysis:
    """Complete loop analysis results for a function."""
    function_name: str
    loops: list[LoopDetail] = field(default_factory=list)

    @property
    def max_depth(self) -> int:
        """Maximum loop nesting depth."""
        if not self.loops:
            return 0
        return max(l.max_child_depth for l in self.loops if l.depth == 1)

    @property
    def total_loops(self) -> int:
        return len(self.loops)

    @property
    def nested_loops(self) -> list[LoopDetail]:
        """Loops with depth > 1."""
        return [l for l in self.loops if l.depth > 1]

    def get_deepest_nesting(self) -> list[LoopDetail]:
        """Get the most deeply nested loops."""
        if not self.loops:
            return []
        max_d = max(l.depth for l in self.loops)
        return [l for l in self.loops if l.depth == max_d]


class _LoopVisitor(ast.NodeVisitor):
    """AST visitor that detects and analyzes all loop constructs."""

    def __init__(self) -> None:
        self.loops: list[LoopDetail] = []
        self._loop_stack: list[LoopDetail] = []
        self._current_depth = 0

    def _push_loop(self, detail: LoopDetail) -> LoopDetail:
        if self._loop_stack:
            parent = self._loop_stack[-1]
            detail.parent = parent
            parent.children.append(detail)
        self._loop_stack.append(detail)
        self.loops.append(detail)
        return detail

    def _pop_loop(self) -> None:
        if self._loop_stack:
            self._loop_stack.pop()

    def visit_For(self, node: ast.For) -> None:
        self._current_depth += 1
        loop_var = self._extract_loop_var(node)
        iterable_str = self._get_iterable_str(node.iter)

        detail = LoopDetail(
            kind=LoopKind.FOR,
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
            col_offset=node.col_offset,
            depth=self._current_depth,
            variables=[LoopVariable(
                name=loop_var,
                lineno=node.lineno,
                iterable=iterable_str,
                iterable_node=node.iter,
            )],
            body_line_count=(node.end_lineno or node.lineno) - node.lineno,
            node=node,
        )

        self._push_loop(detail)
        self._analyze_loop_body(detail, node.body)
        self.generic_visit(node)
        self._pop_loop()
        self._current_depth -= 1

    def visit_While(self, node: ast.While) -> None:
        self._current_depth += 1

        detail = LoopDetail(
            kind=LoopKind.WHILE,
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
            col_offset=node.col_offset,
            depth=self._current_depth,
            body_line_count=(node.end_lineno or node.lineno) - node.lineno,
            node=node,
        )

        self._push_loop(detail)
        self._analyze_loop_body(detail, node.body)
        self.generic_visit(node)
        self._pop_loop()
        self._current_depth -= 1

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node, LoopKind.LIST_COMP)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node, LoopKind.SET_COMP)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension(node, LoopKind.DICT_COMP)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension(node, LoopKind.GEN_EXPR)

    def _visit_comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp,
        kind: LoopKind,
    ) -> None:
        """Process a comprehension as a loop."""
        for gen in node.generators:
            self._current_depth += 1
            loop_var = self._extract_loop_var_from_target(gen.target)
            iterable_str = self._get_iterable_str(gen.iter)

            detail = LoopDetail(
                kind=kind,
                lineno=node.lineno,
                end_lineno=node.end_lineno or node.lineno,
                col_offset=node.col_offset,
                depth=self._current_depth,
                variables=[LoopVariable(
                    name=loop_var,
                    lineno=node.lineno,
                    iterable=iterable_str,
                    iterable_node=gen.iter,
                )],
                node=node,
            )
            self._push_loop(detail)

        self.generic_visit(node)

        for _ in node.generators:
            self._pop_loop()
            self._current_depth -= 1

    def _analyze_loop_body(self, detail: LoopDetail, body: list[ast.stmt]) -> None:
        """Analyze loop body for patterns."""
        loop_vars = {v.name for v in detail.variables}

        for stmt in body:
            for child in ast.walk(stmt):
                if isinstance(child, ast.Break):
                    detail.contains_break = True
                elif isinstance(child, ast.Continue):
                    detail.contains_continue = True
                elif isinstance(child, ast.Return):
                    detail.contains_return = True
                elif isinstance(child, ast.Call):
                    call_name = self._get_call_name(child)
                    detail.function_calls.append(call_name)

                    # Detect expensive operations in loops
                    if call_name in ("sorted", "sort", "list.sort"):
                        detail.has_expensive_operation = True
                        detail.expensive_operations.append(
                            f"Sorting inside loop at line {child.lineno}"
                        )
                    elif call_name in ("open", "json.loads", "json.dumps"):
                        detail.has_expensive_operation = True
                        detail.expensive_operations.append(
                            f"I/O operation '{call_name}' inside loop at line {child.lineno}"
                        )

        # Detect loop-invariant statements
        for stmt in body:
            if isinstance(stmt, (ast.For, ast.While)):
                continue  # skip nested loops
            stmt_reads = self._get_all_names_read(stmt)
            # If no loop variables are read, it might be invariant
            if loop_vars and not (stmt_reads & loop_vars):
                # But only if it writes something (otherwise it might be a side effect)
                stmt_writes = self._get_all_names_written(stmt)
                if stmt_writes and not isinstance(stmt, ast.Expr):
                    detail.has_invariant_code = True
                    detail.invariant_lines.append(stmt.lineno)

    def _extract_loop_var(self, node: ast.For) -> str:
        return self._extract_loop_var_from_target(node.target)

    def _extract_loop_var_from_target(self, target: ast.expr) -> str:
        if isinstance(target, ast.Name):
            return target.id
        elif isinstance(target, ast.Tuple):
            return ", ".join(
                self._extract_loop_var_from_target(e) for e in target.elts
            )
        return "_"

    def _get_iterable_str(self, node: ast.expr) -> str:
        """Get a human-readable string for what's being iterated."""
        if isinstance(node, ast.Call):
            func_name = self._get_call_name(node)
            if func_name == "range":
                args = []
                for arg in node.args:
                    if isinstance(arg, ast.Constant):
                        args.append(str(arg.value))
                    elif isinstance(arg, ast.Name):
                        args.append(arg.id)
                    else:
                        args.append("?")
                return f"range({', '.join(args)})"
            return f"{func_name}(...)"
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_attr_str(node)
        elif isinstance(node, ast.Subscript):
            return f"{self._get_iterable_str(node.value)}[...]"
        return "<expr>"

    def _get_attr_str(self, node: ast.Attribute) -> str:
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._get_attr_str(node.value)}.{node.attr}"
        return node.attr

    def _get_call_name(self, node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return self._get_attr_str(node.func)
        return "<call>"

    def _get_all_names_read(self, node: ast.AST) -> set[str]:
        names: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                names.add(child.id)
        return names

    def _get_all_names_written(self, node: ast.AST) -> set[str]:
        names: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                names.add(child.id)
        return names


def detect_loops(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> LoopAnalysis:
    """Detect and analyze all loops in a function.

    Detects:
    - for loops, while loops, and all comprehension types
    - Nesting depth and parent-child relationships
    - Loop-invariant code
    - Expensive operations inside loops (sorting, I/O)
    - Break/continue/return in loops
    - Function calls inside loops

    Args:
        func_node: Function AST node to analyze.

    Returns:
        LoopAnalysis with detailed information about all loops.
    """
    visitor = _LoopVisitor()
    visitor.visit(func_node)

    return LoopAnalysis(
        function_name=func_node.name,
        loops=visitor.loops,
    )
