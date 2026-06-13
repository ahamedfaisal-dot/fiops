"""Symbol table construction and scope tracking."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum


class SymbolKind(Enum):
    """Kind of symbol."""
    FUNCTION = "function"
    CLASS = "class"
    VARIABLE = "variable"
    PARAMETER = "parameter"
    IMPORT = "import"
    MODULE = "module"


class ScopeType(Enum):
    """Type of scope."""
    GLOBAL = "global"
    CLASS = "class"
    FUNCTION = "function"
    COMPREHENSION = "comprehension"


@dataclass
class Symbol:
    """A single symbol in the symbol table."""
    name: str
    kind: SymbolKind
    lineno: int
    scope: str  # scope path, e.g., "module.ClassName.method_name"
    is_used: bool = False
    usage_lines: list[int] = field(default_factory=list)
    is_assigned: bool = True
    assigned_lines: list[int] = field(default_factory=list)


@dataclass
class Scope:
    """A lexical scope containing symbols."""
    name: str
    scope_type: ScopeType
    parent: Scope | None = None
    symbols: dict[str, Symbol] = field(default_factory=dict)
    children: list[Scope] = field(default_factory=list)

    @property
    def qualified_name(self) -> str:
        """Full qualified name of this scope."""
        parts = []
        current: Scope | None = self
        while current and current.scope_type != ScopeType.GLOBAL:
            parts.append(current.name)
            current = current.parent
        return ".".join(reversed(parts)) if parts else "<module>"

    def lookup(self, name: str) -> Symbol | None:
        """Look up a symbol, searching parent scopes."""
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def define(self, symbol: Symbol) -> None:
        """Define a symbol in this scope."""
        self.symbols[symbol.name] = symbol


@dataclass
class SymbolTable:
    """Complete symbol table for a module."""
    global_scope: Scope
    all_symbols: list[Symbol] = field(default_factory=list)

    def get_unused_symbols(self) -> list[Symbol]:
        """Get all symbols that were defined but never used."""
        return [s for s in self.all_symbols if not s.is_used and s.kind != SymbolKind.IMPORT]

    def get_unused_imports(self) -> list[Symbol]:
        """Get import symbols that were never referenced."""
        return [s for s in self.all_symbols if not s.is_used and s.kind == SymbolKind.IMPORT]


class _SymbolTableBuilder(ast.NodeVisitor):
    """AST visitor that builds a symbol table with scope tracking."""

    def __init__(self) -> None:
        self.global_scope = Scope(name="<module>", scope_type=ScopeType.GLOBAL)
        self.current_scope = self.global_scope
        self.all_symbols: list[Symbol] = []
        # Track all name references for usage analysis
        self._name_references: list[tuple[str, int]] = []

    def _push_scope(self, name: str, scope_type: ScopeType) -> Scope:
        scope = Scope(name=name, scope_type=scope_type, parent=self.current_scope)
        self.current_scope.children.append(scope)
        self.current_scope = scope
        return scope

    def _pop_scope(self) -> None:
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent

    def _define(self, name: str, kind: SymbolKind, lineno: int) -> Symbol:
        sym = Symbol(
            name=name,
            kind=kind,
            lineno=lineno,
            scope=self.current_scope.qualified_name,
            is_assigned=True,
            assigned_lines=[lineno],
        )
        self.current_scope.define(sym)
        self.all_symbols.append(sym)
        return sym

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._define(node.name, SymbolKind.FUNCTION, node.lineno)
        self._push_scope(node.name, ScopeType.FUNCTION)

        # Parameters
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            self._define(arg.arg, SymbolKind.PARAMETER, arg.lineno)
        if node.args.vararg:
            self._define(node.args.vararg.arg, SymbolKind.PARAMETER, node.args.vararg.lineno)
        if node.args.kwarg:
            self._define(node.args.kwarg.arg, SymbolKind.PARAMETER, node.args.kwarg.lineno)

        self.generic_visit(node)
        self._pop_scope()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._define(node.name, SymbolKind.CLASS, node.lineno)
        self._push_scope(node.name, ScopeType.CLASS)
        self.generic_visit(node)
        self._pop_scope()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self._define(name, SymbolKind.IMPORT, node.lineno)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self._define(name, SymbolKind.IMPORT, node.lineno)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._visit_assign_target(target, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name):
            self._define(node.target.id, SymbolKind.VARIABLE, node.lineno)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._visit_assign_target(node.target, node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self._name_references.append((node.id, node.lineno))
        self.generic_visit(node)

    def _visit_assign_target(self, target: ast.expr, lineno: int) -> None:
        if isinstance(target, ast.Name):
            self._define(target.id, SymbolKind.VARIABLE, lineno)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._visit_assign_target(elt, lineno)

    def _resolve_usages(self) -> None:
        """After visiting, mark symbols as used based on name references."""
        for name, lineno in self._name_references:
            for sym in self.all_symbols:
                if sym.name == name:
                    sym.is_used = True
                    sym.usage_lines.append(lineno)
                    break  # mark the first match


def build_symbol_table(tree: ast.Module) -> SymbolTable:
    """Build a symbol table from an AST.

    Args:
        tree: Parsed AST module.

    Returns:
        SymbolTable with all symbols and scope information.
    """
    builder = _SymbolTableBuilder()
    builder.visit(tree)
    builder._resolve_usages()

    return SymbolTable(
        global_scope=builder.global_scope,
        all_symbols=builder.all_symbols,
    )
