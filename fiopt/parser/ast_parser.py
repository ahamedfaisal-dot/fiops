"""Python AST parsing and structured representation."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class FunctionInfo:
    """Information about a parsed function."""
    name: str
    lineno: int
    end_lineno: int
    col_offset: int
    args: list[str]
    decorators: list[str]
    docstring: str | None
    is_method: bool
    is_async: bool
    is_generator: bool
    is_property: bool
    node: ast.FunctionDef | ast.AsyncFunctionDef
    body_line_count: int
    # Nested function names
    nested_functions: list[str] = field(default_factory=list)

    @property
    def source_range(self) -> tuple[int, int]:
        """Return (start_line, end_line) tuple."""
        return (self.lineno, self.end_lineno)


@dataclass
class ClassInfo:
    """Information about a parsed class."""
    name: str
    lineno: int
    end_lineno: int
    bases: list[str]
    decorators: list[str]
    docstring: str | None
    methods: list[FunctionInfo]
    node: ast.ClassDef


@dataclass
class ParsedModule:
    """Structured representation of a parsed Python module."""
    tree: ast.Module
    source: str
    functions: list[FunctionInfo]
    classes: list[ClassInfo]
    top_level_statements: int
    imports: list[ast.Import | ast.ImportFrom]
    global_variables: list[str]

    @property
    def all_functions(self) -> list[FunctionInfo]:
        """Get all functions, including methods inside classes."""
        result = list(self.functions)
        for cls in self.classes:
            result.extend(cls.methods)
        return result

    def get_function(self, name: str) -> FunctionInfo | None:
        """Find a function by name."""
        for func in self.all_functions:
            if func.name == name:
                return func
        return None

    def iter_functions(self) -> Iterator[FunctionInfo]:
        """Iterate over all functions."""
        yield from self.all_functions


def _extract_decorator_name(node: ast.expr) -> str:
    """Extract decorator name as string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    if isinstance(node, ast.Call):
        return _extract_decorator_name(node.func)
    return "<unknown>"


def _get_docstring(node: ast.AST) -> str | None:
    """Extract docstring from a node if present."""
    if (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        return node.body[0].value.value
    return None


def _is_generator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a function contains yield/yield from."""
    for child in ast.walk(node):
        if isinstance(child, (ast.Yield, ast.YieldFrom)):
            return True
    return False


def _extract_arg_names(arguments: ast.arguments) -> list[str]:
    """Extract argument names from function signature."""
    names = []
    for arg in arguments.posonlyargs:
        names.append(arg.arg)
    for arg in arguments.args:
        names.append(arg.arg)
    if arguments.vararg:
        names.append(f"*{arguments.vararg.arg}")
    for arg in arguments.kwonlyargs:
        names.append(arg.arg)
    if arguments.kwarg:
        names.append(f"**{arguments.kwarg.arg}")
    return names


def _extract_nested_function_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Find names of functions defined directly inside this function body."""
    names = []
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append(child.name)
    return names


def _parse_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    is_method: bool = False,
) -> FunctionInfo:
    """Parse a function/method definition into FunctionInfo."""
    decorators = [_extract_decorator_name(d) for d in node.decorator_list]
    is_property = "property" in decorators or any(
        "setter" in d or "getter" in d or "deleter" in d for d in decorators
    )

    end_lineno = node.end_lineno or node.lineno
    body_line_count = end_lineno - node.lineno

    return FunctionInfo(
        name=node.name,
        lineno=node.lineno,
        end_lineno=end_lineno,
        col_offset=node.col_offset,
        args=_extract_arg_names(node.args),
        decorators=decorators,
        docstring=_get_docstring(node),
        is_method=is_method,
        is_async=isinstance(node, ast.AsyncFunctionDef),
        is_generator=_is_generator(node),
        is_property=is_property,
        node=node,
        body_line_count=body_line_count,
        nested_functions=_extract_nested_function_names(node),
    )


def _parse_class(node: ast.ClassDef) -> ClassInfo:
    """Parse a class definition into ClassInfo."""
    bases = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            bases.append(base.id)
        elif isinstance(base, ast.Attribute):
            bases.append(_extract_decorator_name(base))
        else:
            bases.append("<expr>")

    methods = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_parse_function(item, is_method=True))

    return ClassInfo(
        name=node.name,
        lineno=node.lineno,
        end_lineno=node.end_lineno or node.lineno,
        bases=bases,
        decorators=[_extract_decorator_name(d) for d in node.decorator_list],
        docstring=_get_docstring(node),
        methods=methods,
        node=node,
    )


def parse(source: str, filename: str = "<string>") -> ParsedModule:
    """Parse Python source code into a structured ParsedModule.

    Args:
        source: Python source code string.
        filename: Filename for error messages.

    Returns:
        ParsedModule with AST, functions, classes, and metadata.

    Raises:
        SyntaxError: If the source code has syntax errors.
    """
    tree = ast.parse(source, filename=filename)

    functions: list[FunctionInfo] = []
    classes: list[ClassInfo] = []
    imports: list[ast.Import | ast.ImportFrom] = []
    global_vars: list[str] = []
    top_level_count = 0

    for node in tree.body:
        top_level_count += 1
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(_parse_function(node))
        elif isinstance(node, ast.ClassDef):
            classes.append(_parse_class(node))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(node)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    global_vars.append(target.id)
                elif isinstance(target, ast.Tuple):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            global_vars.append(elt.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            global_vars.append(node.target.id)

    return ParsedModule(
        tree=tree,
        source=source,
        functions=functions,
        classes=classes,
        top_level_statements=top_level_count,
        imports=imports,
        global_variables=global_vars,
    )
