"""Import graph construction and dependency mapping."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from fiopt.parser.source_loader import SourceFile


@dataclass
class ImportInfo:
    """Information about a single import statement."""
    module: str              # e.g., "os.path" or "collections"
    names: list[str]         # e.g., ["defaultdict", "Counter"] for from-imports
    alias: str | None        # e.g., "np" for "import numpy as np"
    lineno: int
    is_from_import: bool     # True for 'from X import Y'
    is_relative: bool        # True for relative imports (from . import X)
    is_stdlib: bool = False  # Will be set based on module name
    is_internal: bool = False  # True if module is part of the project


# Known stdlib top-level modules (Python 3.10+)
_STDLIB_MODULES = frozenset({
    "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
    "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
    "binhex", "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb",
    "chunk", "cmath", "cmd", "code", "codecs", "codeop", "collections",
    "colorsys", "compileall", "concurrent", "configparser", "contextlib",
    "contextvars", "copy", "copyreg", "cProfile", "crypt", "csv",
    "ctypes", "curses", "dataclasses", "datetime", "dbm", "decimal",
    "difflib", "dis", "distutils", "doctest", "email", "encodings",
    "enum", "errno", "faulthandler", "fcntl", "filecmp", "fileinput",
    "fnmatch", "fractions", "ftplib", "functools", "gc", "getopt",
    "getpass", "gettext", "glob", "graphlib", "grp", "gzip", "hashlib",
    "heapq", "hmac", "html", "http", "idlelib", "imaplib", "imghdr",
    "imp", "importlib", "inspect", "io", "ipaddress", "itertools",
    "json", "keyword", "lib2to3", "linecache", "locale", "logging",
    "lzma", "mailbox", "mailcap", "marshal", "math", "mimetypes",
    "mmap", "modulefinder", "multiprocessing", "netrc", "nis", "nntplib",
    "numbers", "operator", "optparse", "os", "ossaudiodev", "pathlib",
    "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform",
    "plistlib", "poplib", "posix", "posixpath", "pprint", "profile",
    "pstats", "pty", "pwd", "py_compile", "pyclbr", "pydoc",
    "queue", "quopri", "random", "re", "readline", "reprlib",
    "resource", "rlcompleter", "runpy", "sched", "secrets", "select",
    "selectors", "shelve", "shlex", "shutil", "signal", "site",
    "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd",
    "sqlite3", "sre_compile", "sre_constants", "sre_parse", "ssl",
    "stat", "statistics", "string", "stringprep", "struct", "subprocess",
    "sunau", "symtable", "sys", "sysconfig", "syslog", "tabnanny",
    "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap",
    "threading", "time", "timeit", "tkinter", "token", "tokenize",
    "tomllib", "trace", "traceback", "tracemalloc", "tty", "turtle",
    "turtledemo", "types", "typing", "unicodedata", "unittest", "urllib",
    "uu", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
    "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc",
    "zipapp", "zipfile", "zipimport", "zlib", "_thread",
})


def _is_stdlib(module_name: str) -> bool:
    """Check if a module is part of the Python standard library."""
    top_level = module_name.split(".")[0]
    return top_level in _STDLIB_MODULES


@dataclass
class ImportGraph:
    """Dependency graph between modules."""
    # module_path -> list of ImportInfo
    imports_by_file: dict[str, list[ImportInfo]] = field(default_factory=dict)
    # module_name -> set of files that import it
    imported_by: dict[str, set[str]] = field(default_factory=dict)
    # Internal module names (files within the project)
    internal_modules: set[str] = field(default_factory=set)

    @property
    def external_dependencies(self) -> set[str]:
        """Get all external (non-stdlib, non-internal) dependencies."""
        external = set()
        for imports in self.imports_by_file.values():
            for imp in imports:
                if not imp.is_stdlib and not imp.is_internal:
                    external.add(imp.module.split(".")[0])
        return external

    def get_imports(self, filepath: str) -> list[ImportInfo]:
        """Get all imports for a specific file."""
        return self.imports_by_file.get(filepath, [])

    def detect_circular_dependencies(self) -> list[tuple[str, str]]:
        """Detect circular import dependencies between internal modules.

        Returns:
            List of (module_a, module_b) pairs with circular imports.
        """
        circular: list[tuple[str, str]] = []
        checked: set[tuple[str, str]] = set()

        for filepath, imports in self.imports_by_file.items():
            for imp in imports:
                if imp.is_internal and imp.module in self.imports_by_file:
                    pair = tuple(sorted((filepath, imp.module)))
                    if pair not in checked:
                        checked.add(pair)
                        # Check if the other module imports this one
                        other_imports = self.imports_by_file.get(imp.module, [])
                        for other_imp in other_imports:
                            if other_imp.module == filepath or filepath.endswith(
                                other_imp.module.replace(".", "/") + ".py"
                            ):
                                circular.append((filepath, imp.module))
                                break

        return circular


def _extract_imports(tree: ast.Module) -> list[ImportInfo]:
    """Extract all import statements from an AST."""
    imports: list[ImportInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(ImportInfo(
                    module=alias.name,
                    names=[],
                    alias=alias.asname,
                    lineno=node.lineno,
                    is_from_import=False,
                    is_relative=False,
                    is_stdlib=_is_stdlib(alias.name),
                ))
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            names = [alias.name for alias in node.names]
            is_relative = (node.level or 0) > 0

            imports.append(ImportInfo(
                module=module_name,
                names=names,
                alias=None,
                lineno=node.lineno,
                is_from_import=True,
                is_relative=is_relative,
                is_stdlib=_is_stdlib(module_name) if module_name else False,
            ))

    return imports


def build_import_graph(files: list[SourceFile]) -> ImportGraph:
    """Build an import dependency graph from a list of source files.

    Args:
        files: List of SourceFile objects to analyze.

    Returns:
        ImportGraph with dependency information.
    """
    graph = ImportGraph()

    # Determine internal module names based on file paths
    for f in files:
        # Convert file path to module-like name
        module_name = f.path.stem
        graph.internal_modules.add(module_name)

    for f in files:
        filepath = str(f.path)
        try:
            tree = ast.parse(f.content, filename=filepath)
        except SyntaxError:
            continue

        imports = _extract_imports(tree)

        # Mark internal imports
        for imp in imports:
            top_level = imp.module.split(".")[0] if imp.module else ""
            if top_level in graph.internal_modules or imp.is_relative:
                imp.is_internal = True

            # Track reverse dependency
            if imp.module:
                if imp.module not in graph.imported_by:
                    graph.imported_by[imp.module] = set()
                graph.imported_by[imp.module].add(filepath)

        graph.imports_by_file[filepath] = imports

    return graph
