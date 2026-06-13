"""Source file loading and project scanning."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SourceFile:
    """Represents a loaded Python source file."""
    path: Path
    content: str
    line_count: int
    encoding: str = "utf-8"

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def lines(self) -> list[str]:
        return self.content.splitlines()

    def get_line(self, lineno: int) -> str:
        """Get a specific line (1-indexed)."""
        lines = self.lines
        if 1 <= lineno <= len(lines):
            return lines[lineno - 1]
        return ""

    def get_lines(self, start: int, end: int) -> str:
        """Get a range of lines (1-indexed, inclusive)."""
        lines = self.lines
        start = max(1, start)
        end = min(len(lines), end)
        return "\n".join(lines[start - 1 : end])


def load_file(path: str | Path) -> SourceFile:
    """Load a single Python file.

    Args:
        path: Path to the Python file.

    Returns:
        SourceFile with the loaded content.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file is not a Python file.
    """
    path = Path(path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix != ".py":
        raise ValueError(f"Not a Python file: {path}")

    encoding = "utf-8"
    try:
        content = path.read_text(encoding=encoding)
    except UnicodeDecodeError:
        # Fall back to latin-1 which can read any byte sequence
        encoding = "latin-1"
        content = path.read_text(encoding=encoding)

    return SourceFile(
        path=path,
        content=content,
        line_count=content.count("\n") + (1 if content and not content.endswith("\n") else 0),
        encoding=encoding,
    )


def scan_project(
    directory: str | Path,
    extensions: list[str] | None = None,
    exclude_dirs: list[str] | None = None,
) -> list[SourceFile]:
    """Recursively find and load all Python files in a directory.

    Args:
        directory: Root directory to scan.
        extensions: File extensions to include (default: [".py"]).
        exclude_dirs: Directory names to exclude.

    Returns:
        List of loaded SourceFiles, sorted by path.
    """
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    if extensions is None:
        extensions = [".py"]
    if exclude_dirs is None:
        exclude_dirs = [
            "__pycache__", ".git", ".venv", "venv", "node_modules",
            ".tox", ".eggs", "dist", "build", ".mypy_cache",
        ]

    exclude_set = set(exclude_dirs)
    files: list[SourceFile] = []

    for root, dirs, filenames in os.walk(directory):
        # Filter excluded directories in-place to prevent os.walk from descending
        dirs[:] = [d for d in dirs if d not in exclude_set]

        for fname in sorted(filenames):
            fpath = Path(root) / fname
            if fpath.suffix in extensions:
                try:
                    files.append(load_file(fpath))
                except (ValueError, UnicodeDecodeError):
                    continue

    return sorted(files, key=lambda f: f.path)
