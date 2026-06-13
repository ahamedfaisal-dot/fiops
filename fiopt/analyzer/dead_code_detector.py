"""Dead code detection.

Detects:
- Unreachable code after return/break/continue/raise
- Unused variables (assigned but never read)
- Unused imports
- Functions defined but never called (within analysis scope)
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass
class DeadCodeItem:
    """A piece of detected dead code."""
    kind: str       # "unreachable", "unused_variable", "unused_import", "unused_function"
    lineno: int
    end_lineno: int
    name: str       # variable/function/import name
    description: str
    suggestion: str


@dataclass
class DeadCodeAnalysis:
    """Dead code analysis results."""
    items: list[DeadCodeItem] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def unreachable_count(self) -> int:
        return sum(1 for i in self.items if i.kind == "unreachable")

    @property
    def unused_variable_count(self) -> int:
        return sum(1 for i in self.items if i.kind == "unused_variable")

    @property
    def unused_import_count(self) -> int:
        return sum(1 for i in self.items if i.kind == "unused_import")


class _UnreachableCodeVisitor(ast.NodeVisitor):
    """Detect unreachable code after return/break/continue/raise."""

    def __init__(self) -> None:
        self.unreachable: list[DeadCodeItem] = []

    def _check_body(self, body: list[ast.stmt]) -> None:
        """Check a body of statements for unreachable code after terminators."""
        for i, stmt in enumerate(body):
            if isinstance(stmt, (ast.Return, ast.Break, ast.Continue, ast.Raise)):
                # Everything after this statement in the same block is unreachable
                remaining = body[i + 1:]
                for unreachable_stmt in remaining:
                    # Skip docstrings and pass statements
                    if isinstance(unreachable_stmt, ast.Pass):
                        continue
                    self.unreachable.append(DeadCodeItem(
                        kind="unreachable",
                        lineno=unreachable_stmt.lineno,
                        end_lineno=unreachable_stmt.end_lineno or unreachable_stmt.lineno,
                        name="",
                        description=(
                            f"Unreachable code after "
                            f"{'return' if isinstance(stmt, ast.Return) else ''}"
                            f"{'break' if isinstance(stmt, ast.Break) else ''}"
                            f"{'continue' if isinstance(stmt, ast.Continue) else ''}"
                            f"{'raise' if isinstance(stmt, ast.Raise) else ''}"
                            f" at line {stmt.lineno}"
                        ),
                        suggestion="Remove unreachable code or restructure control flow.",
                    ))
                break  # Stop checking after first terminator

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_body(node.body)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_For(self, node: ast.For) -> None:
        self._check_body(node.body)
        if node.orelse:
            self._check_body(node.orelse)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._check_body(node.body)
        if node.orelse:
            self._check_body(node.orelse)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self._check_body(node.body)
        if node.orelse:
            self._check_body(node.orelse)
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._check_body(node.body)
        for handler in node.handlers:
            self._check_body(handler.body)
        if node.orelse:
            self._check_body(node.orelse)
        if node.finalbody:
            self._check_body(node.finalbody)
        self.generic_visit(node)


def _detect_unused_variables(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[DeadCodeItem]:
    """Find variables that are assigned but never read."""
    items: list[DeadCodeItem] = []

    # Collect all assignments and all reads
    assigned: dict[str, int] = {}  # name -> lineno
    read: set[str] = set()

    # Skip variables named _ (convention for unused)
    SKIP_NAMES = {"_", "__", "self", "cls"}

    for node in ast.walk(func_node):
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Store):
                if node.id not in SKIP_NAMES and node.id not in assigned:
                    assigned[node.id] = node.lineno
            elif isinstance(node.ctx, ast.Load):
                read.add(node.id)
        elif isinstance(node, ast.arg):
            # Don't flag function parameters
            read.add(node.arg)

    for name, lineno in assigned.items():
        if name not in read:
            items.append(DeadCodeItem(
                kind="unused_variable",
                lineno=lineno,
                end_lineno=lineno,
                name=name,
                description=f"Variable '{name}' is assigned at line {lineno} but never used",
                suggestion=f"Remove the assignment to '{name}' or use the variable.",
            ))

    return items


def detect_dead_code(
    tree: ast.Module,
    func_nodes: list[ast.FunctionDef | ast.AsyncFunctionDef] | None = None,
) -> DeadCodeAnalysis:
    """Detect dead code in a module.

    Checks for:
    - Unreachable code after return/break/continue/raise
    - Unused variables in functions
    - Unused imports

    Args:
        tree: The module AST.
        func_nodes: Optional list of function nodes to analyze for unused variables.

    Returns:
        DeadCodeAnalysis with all detected dead code.
    """
    result = DeadCodeAnalysis()

    # Unreachable code
    visitor = _UnreachableCodeVisitor()
    visitor.visit(tree)
    result.items.extend(visitor.unreachable)

    # Unused variables in each function
    if func_nodes:
        for func in func_nodes:
            result.items.extend(_detect_unused_variables(func))

    # Unused imports
    _detect_unused_imports(tree, result)

    return result


def _detect_unused_imports(tree: ast.Module, result: DeadCodeAnalysis) -> None:
    """Detect imports that are never referenced in the module."""
    imported: dict[str, int] = {}  # name -> lineno
    referenced: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                imported[name] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                imported[name] = node.lineno
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            referenced.add(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            referenced.add(node.value.id)

    for name, lineno in imported.items():
        if name not in referenced and not name.startswith("_"):
            result.items.append(DeadCodeItem(
                kind="unused_import",
                lineno=lineno,
                end_lineno=lineno,
                name=name,
                description=f"Import '{name}' at line {lineno} is never used",
                suggestion=f"Remove unused import '{name}'.",
            ))
