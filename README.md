# FiOpt — AI-Powered Code Complexity & Optimization Engine

> *"Analyze. Detect. Accelerate."*

Developed by **Ahamed Faisal**

FiOpt is a compiler-inspired static analysis tool for Python that automatically estimates Big-O complexity, detects performance bottlenecks, finds anti-patterns, and suggests optimizations — all without running your code.

```
Source Code → Parser → AST → Analysis → Report
```

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Python API](#python-api)
- [What FiOpt Detects](#what-fiopt-detects)
- [Output Formats](#output-formats)
- [Configuration](#configuration)
- [Examples](#examples)
- [Architecture](#architecture)
- [Running Tests](#running-tests)
- [License](#license)

---

## Features

| Feature | Description |
|---|---|
| **Big-O Complexity Detection** | Automatically estimates time complexity for every function — O(1), O(log n), O(n), O(n log n), O(n²), O(n³), O(2ⁿ), and more |
| **Loop & Nesting Analysis** | Detects nested loops, unnecessary iterations, and loop-invariant code |
| **Recursion Detection** | Finds recursive functions, missing memoization opportunities, tail-recursion candidates |
| **Anti-Pattern Detection** | List-vs-set misuse, string concatenation in loops, sorting inside loops, poor data structure choices |
| **Dead Code Detection** | Unreachable code, unused variables, uncalled functions |
| **Rich Reports** | Beautiful terminal output (via Rich), standalone HTML reports, machine-readable JSON |

---

## Requirements

- **Python 3.10+**
- No external dependencies beyond `click`, `rich`, and `jinja2` (installed automatically)

---

## Installation

### From source (recommended for development)

```bash
# Clone the repository
git clone https://github.com/your-org/fiopt.git
cd fiopt

# Create a virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install in editable mode
pip install -e .
```

### Install with dev dependencies (for running tests)

```bash
pip install -e ".[dev]"
```

After installation, the `fiopt` command is available in your terminal.

---

## Quick Start

### Analyze a file from the terminal

```bash
fiopt analyze app.py
```

### Analyze with verbose explanations

```bash
fiopt analyze app.py -v
```

### Analyze an entire project

```bash
fiopt analyze src/
```

### Generate an HTML report

```bash
fiopt analyze src/ --format html -o report.html
```

### Get JSON output (for CI pipelines)

```bash
fiopt analyze app.py --format json -o results.json
```

### Use as a Python library

```python
from fiopt import analyze

report = analyze("main.py")

print(report.complexity)   # e.g. "O(n²)"
print(report.bottlenecks)  # List of performance bottlenecks
print(report.suggestions)  # Optimization recommendations
```

---

## CLI Reference

```
fiopt analyze [OPTIONS] PATH
```

| Option | Short | Description | Default |
|---|---|---|---|
| `--format` | `-f` | Output format: `terminal`, `html`, or `json` | `terminal` |
| `--output` | `-o` | Output file path (for html/json) | — |
| `--verbose` | `-v` | Show detailed complexity explanations | off |
| `--no-dead-code` | — | Skip dead code detection | off |
| `--no-patterns` | — | Skip anti-pattern detection | off |
| `--threshold` | — | Complexity threshold for warnings: `O(n)`, `O(n²)`, `O(n³)` | `O(n²)` |

**`PATH`** can be a single `.py` file or a directory. When given a directory, FiOpt recursively analyzes all Python files (excluding `__pycache__`, `.venv`, `venv`, `node_modules`, etc.).

### Other commands

```bash
fiopt version           # Show version and system info
fiopt --help            # Show top-level help
fiopt analyze --help    # Show analyze command help
```

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Analysis complete, no critical issues |
| `1` | Critical issues found (complexity ≥ threshold) |

This makes FiOpt suitable for **CI/CD pipelines** — fail the build when critical performance issues are detected:

```yaml
# GitHub Actions example
- name: Check code complexity
  run: fiopt analyze src/ --threshold "O(n²)"
```

---

## Python API

FiOpt exposes two primary functions:

### `analyze(path, config=None)`

Analyze a Python file or directory.

```python
from fiopt import analyze

# Analyze a file
report = analyze("main.py")

# Analyze a directory
report = analyze("src/")

# With custom configuration
from fiopt.config import AnalysisConfig, ComplexityClass

config = AnalysisConfig(
    complexity_warning_threshold=ComplexityClass.O_N,
    detect_dead_code=False,
)
report = analyze("main.py", config=config)
```

### `analyze_source(source, filename="<string>", config=None)`

Analyze a Python source code string directly — useful for testing, notebooks, or dynamic code.

```python
from fiopt import analyze_source

report = analyze_source("""
def bubble_sort(arr):
    for i in range(len(arr)):
        for j in range(len(arr) - 1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
""")

print(report.complexity)   # "O(n²)"
print(report.bottlenecks)  # ["<string>:bubble_sort (L2) — O(n²): ..."]
print(report.suggestions)  # Optimization suggestions
print(report.summary)      # Full human-readable summary
```

### Report object

The `AnalysisReport` returned by both functions provides:

| Property | Type | Description |
|---|---|---|
| `report.complexity` | `str` | Worst-case complexity as string (e.g. `"O(n²)"`) |
| `report.bottlenecks` | `list[str]` | Human-readable bottleneck descriptions |
| `report.suggestions` | `list[str]` | Optimization recommendations |
| `report.summary` | `str` | Full human-readable summary |
| `report.total_files` | `int` | Number of files analyzed |
| `report.total_functions` | `int` | Number of functions analyzed |
| `report.total_issues` | `int` | Total issues found |
| `report.worst_complexity` | `ComplexityClass` | Worst complexity as enum |
| `report.analysis_duration_ms` | `float` | Analysis time in milliseconds |
| `report.files` | `list[FileReport]` | Per-file detailed reports |

Each `FileReport` contains `function_reports` with per-function details including:
- **Complexity** — estimated Big-O, confidence score, bottleneck lines, explanations
- **Anti-patterns** — detected code smells with suggestions
- **Data structure issues** — misuse of lists vs sets, etc.
- **Dead code** — unreachable code, unused variables

---

## What FiOpt Detects

### Complexity Classes

FiOpt can identify and distinguish these complexity classes:

| Class | Example | Detection Method |
|---|---|---|
| **O(1)** | `return a + b` | No loops, constant-bound loops, dict lookups |
| **O(log n)** | Binary search | While loops with halving patterns, recursive divide-and-conquer |
| **O(n)** | `for x in arr` | Single loops over input, linear recursion |
| **O(n log n)** | `sorted(arr)` | Known stdlib calls, sort-inside-loop detection |
| **O(n²)** | Nested loops | Two nested loops over input |
| **O(n³)** | Matrix multiply | Triple nested loops |
| **O(2ⁿ)** | Naive fibonacci | Branching recursion with overlapping subproblems |

### Anti-Patterns

- **List membership in loops** — `if x in my_list` inside a loop → suggest `set`
- **String concatenation in loops** — `result += s` → suggest `"".join()`
- **Sorting inside loops** — `sorted()` called repeatedly → move outside loop
- **Loop-invariant code** — Computation that can be hoisted outside the loop
- **Unnecessary list append** — Suggest list comprehension

### Recursion Analysis

- **Missing memoization** — Detects overlapping subproblems (e.g., naive fibonacci)
- **Tail recursion candidates** — Functions that could be converted to iteration
- **Missing base case** — Warns about potential infinite recursion
- **Branching analysis** — Correctly handles mutually exclusive branches (e.g., binary search's `if/elif/else` is 1 branch, not 2)

### Dead Code

- Unreachable code after `return` statements
- Unused variables
- Uncalled functions (when analyzing a directory)

---

## Output Formats

### Terminal (default)

Rich, color-coded output with function tables, severity indicators, and a summary panel:

```bash
fiopt analyze app.py
```

Use `-v` for detailed complexity breakdowns:

```bash
fiopt analyze app.py -v
```

### HTML

Generates a self-contained HTML report that can be shared or hosted:

```bash
fiopt analyze src/ --format html -o report.html
```

### JSON

Machine-readable JSON output for CI/CD integration or further processing:

```bash
# Print to stdout
fiopt analyze app.py --format json

# Save to file
fiopt analyze app.py --format json -o results.json
```

The JSON output includes full analysis details: complexity estimates, confidence scores, explanations, bottleneck lines, anti-patterns, and dead code findings.

---

## Configuration

Use `AnalysisConfig` to customize the analysis when using the Python API:

```python
from fiopt.config import AnalysisConfig, ComplexityClass

config = AnalysisConfig(
    # Flag functions with O(n) or worse as warnings
    complexity_warning_threshold=ComplexityClass.O_N,

    # Flag functions with O(n³) or worse as critical
    complexity_critical_threshold=ComplexityClass.O_N_CUBED,

    # Toggle analysis features
    detect_dead_code=True,
    detect_anti_patterns=True,
    detect_data_structure_issues=True,
    detect_recursion_issues=True,

    # Verbose output
    verbose=True,

    # File filters
    file_extensions=[".py"],
    exclude_dirs=["__pycache__", ".git", "venv", ".venv", "node_modules"],
)
```

| Option | Type | Default | Description |
|---|---|---|---|
| `complexity_warning_threshold` | `ComplexityClass` | `O(n²)` | Severity threshold for warnings |
| `complexity_critical_threshold` | `ComplexityClass` | `O(n³)` | Severity threshold for critical |
| `detect_dead_code` | `bool` | `True` | Enable dead code detection |
| `detect_anti_patterns` | `bool` | `True` | Enable anti-pattern detection |
| `detect_data_structure_issues` | `bool` | `True` | Enable data structure misuse detection |
| `detect_recursion_issues` | `bool` | `True` | Enable recursion analysis |
| `verbose` | `bool` | `False` | Show detailed explanations |
| `file_extensions` | `list[str]` | `[".py"]` | File types to analyze |
| `exclude_dirs` | `list[str]` | *(common dirs)* | Directories to skip |

---

## Examples

The `examples/` directory contains annotated sample files demonstrating various patterns FiOpt detects:

| File | Description |
|---|---|
| `simple_loops.py` | O(1) and O(n) patterns — linear search, summation, constant operations |
| `nested_loops.py` | O(n²) and O(n³) patterns — bubble sort, matrix multiply, string builders |
| `recursive_functions.py` | Recursion patterns — fibonacci, binary search, tail recursion, tree traversal |
| `data_structure_misuse.py` | Anti-patterns — list membership, string concat, sorting in loops |
| `complex_algorithm.py` | Graph algorithms — BFS, Dijkstra, PageRank, community detection |

Try them out:

```bash
# See how FiOpt rates each example
fiopt analyze examples/ -v

# Analyze a specific example
fiopt analyze examples/recursive_functions.py -v

# Get JSON output for the data structure examples
fiopt analyze examples/data_structure_misuse.py --format json
```

---

## Architecture

FiOpt follows a **compiler-inspired pipeline**:

```
Source Code → Parser → AST → Analyzer → Report
```

### Project Structure

```
fiopt/
├── __init__.py              # Package entry point (exports analyze, analyze_source)
├── api.py                   # Public API — analyze() and analyze_source()
├── cli.py                   # Click-based CLI interface
├── config.py                # Configuration and enums (ComplexityClass, Severity)
├── parser/
│   ├── ast_parser.py        # AST parsing and function extraction
│   ├── source_loader.py     # File/directory loading
│   ├── symbol_table.py      # Symbol table construction
│   └── import_graph.py      # Import dependency graph
├── ir/
│   ├── cfg.py               # Control Flow Graph builder
│   ├── basic_block.py       # Basic block representation
│   └── ir_nodes.py          # IR node types
├── analyzer/
│   ├── complexity_estimator.py  # Big-O estimation engine
│   ├── loop_detector.py         # Loop nesting and pattern analysis
│   ├── recursion_detector.py    # Recursion detection and classification
│   ├── pattern_matcher.py       # Anti-pattern detection
│   ├── dead_code_detector.py    # Dead code and unused variable detection
│   └── data_structure_analyzer.py  # Data structure misuse detection
├── reporting/
│   ├── report.py            # Report data model
│   ├── terminal_reporter.py # Rich terminal output
│   ├── html_reporter.py     # Standalone HTML report generator
│   └── json_reporter.py     # JSON output
├── examples/                # Annotated example files
└── tests/                   # Test suite (66 tests)
```

### How Complexity Estimation Works

1. **Loop Analysis** — Detects `for`, `while`, and comprehension loops. Estimates iteration count from the iterable (e.g., `range(n)` → O(n), `range(10)` → O(1)). Nested loop complexities are multiplied.

2. **Recursion Analysis** — Detects direct and mutual recursion. Analyzes branching factor (accounting for mutually exclusive `if/elif/else` branches), depth pattern (linear, logarithmic, exponential), and overlapping subproblems.

3. **Known Function Complexities** — Recognizes stdlib calls (`sorted()` → O(n log n), `list.index()` → O(n), `dict.get()` → O(1)).

4. **Combination** — Takes the maximum of loop, recursion, and call complexities. Nested calls inside loops multiply.

---

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_analyzer/test_complexity_estimator.py -v

# Run with coverage
pytest --cov=fiopt --cov-report=term-missing
```

The test suite covers:
- **Complexity estimation** — O(1) through O(2ⁿ), including edge cases for nested loops, recursion, and known function calls
- **Loop detection** — For/while/comprehension loops, nesting depth, parent-child relationships
- **Recursion detection** — Direct recursion, base case detection, memoization opportunities, tail recursion
- **API** — File analysis, directory analysis, source string analysis, report properties
- **CLI** — All commands, output formats, flags, error handling

---

## License

MIT
