<p align="center">
  <img src="https://img.shields.io/pypi/v/fiops-complexity?color=%2334D058&label=PyPI&logo=pypi&logoColor=white" alt="PyPI Version" />
  <img src="https://img.shields.io/pypi/pyversions/fiops-complexity?logo=python&logoColor=white" alt="Python Versions" />
  <img src="https://img.shields.io/github/license/ahamedfaisal-dot/fiops?color=blue" alt="License" />
  <img src="https://img.shields.io/github/actions/workflow/status/ahamedfaisal-dot/fiops/publish.yml?label=publish&logo=github" alt="Publish Status" />
  <img src="https://img.shields.io/badge/Made%20for-Vibe%20Coders-blueviolet" alt="Made for Vibe Coders" />
</p>

# FiOpt — AI-Powered Code Complexity & Optimization Engine

> *"Analyze. Detect. Accelerate."*

**Developed by [Ahamed Faisal](https://github.com/ahamedfaisal-dot)**

FiOpt is a **compiler-inspired static analysis tool** for Python that automatically estimates Big-O complexity, detects performance bottlenecks, finds anti-patterns, and suggests optimizations — **all without running your code**.

```
Source Code → Parser → AST → Analysis → Report
```

---

## Built for Vibe Coders

FiOpt is **purpose-built for the vibe coding workflow**. If you're a developer who uses AI assistants (ChatGPT, Claude, Copilot, Gemini, Cursor, etc.) to write code, FiOpt is your **quality gate**.

### The Problem

When you vibe-code — letting AI generate large chunks of code — you move fast, but you can't always tell if the generated code is **performant**. AI models can produce working code that silently contains `O(n²)` loops, redundant sorts, or naive recursion that will **break at scale**.

### The Solution

FiOpt analyzes the AI-generated code and produces a **structured report** that you can feed right back to your AI assistant to fix the issues — creating a **self-improving feedback loop**:

```
┌─────────────────────────────────────────────────────────┐
│                   VIBE CODING LOOP                      │
│                                                         │
│   You ──prompt──▶ AI writes code                        │
│                      │                                  │
│                      ▼                                  │
│               FiOpt analyzes it                         │
│                      │                                  │
│                      ▼                                  │
│            Report (bottlenecks,                         │
│            anti-patterns, fixes)                        │
│                      │                                  │
│                      ▼                                  │
│           Feed report back to AI ◀── "Fix these issues" │
│                      │                                  │
│                      ▼                                  │
│              AI improves code                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### How to Use It in Your Vibe Coding Workflow

**Step 1: Generate code with your AI assistant**

Ask your AI to build a feature, function, or module as you normally would.

**Step 2: Run FiOpt on the generated code**

```bash
# Analyze a single file
fiopt analyze generated_code.py -v

# Or get JSON output (best for feeding back to AI)
fiopt analyze generated_code.py --format json
```

**Step 3: Feed the report back to your AI**

Copy the FiOpt output and paste it into your AI assistant with a prompt like:

> *"Here is a performance analysis of the code you wrote. Please fix the bottlenecks and anti-patterns identified in this report:"*

```
[paste FiOpt output here]
```

**Step 4: Repeat until clean**

Run FiOpt again on the improved code. When the report shows no critical issues — you're shipping clean, performant code without manually reading every line.

### Example: Catching AI-Generated Performance Issues

Your AI writes a deduplication function:

```python
def deduplicate(items):
    unique = []
    for item in items:
        if item not in unique:  # O(n) check on every iteration!
            unique.append(item)
    return unique
```

FiOpt catches it:

```
⚠ WARNING: deduplicate (L1) — O(n²)
  └─ List membership check inside loop. Use a set for O(1) lookups.
  └─ Suggestion: Convert 'unique' to a set, or use dict.fromkeys(items)
```

You paste this into your AI, and it fixes it:

```python
def deduplicate(items):
    return list(dict.fromkeys(items))  # O(n)
```

**That's the power of FiOpt + AI. You vibe, FiOpt validates, AI fixes.**

---

## Table of Contents

- [Built for Vibe Coders](#built-for-vibe-coders)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Python API](#python-api)
- [What FiOpt Detects](#what-fiopt-detects)
- [Output Formats](#output-formats)
- [Configuration](#configuration)
- [Real-World Workflows](#real-world-workflows)
- [Examples](#examples)
- [Architecture](#architecture)
- [Running Tests](#running-tests)
- [Troubleshooting & FAQ](#troubleshooting--faq)
- [Contributing](#contributing)
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
| **Vibe-Coder Friendly** | JSON/terminal output designed to be pasted directly into AI assistants for auto-fixing |
| **Zero Runtime Needed** | Pure static analysis — no code execution, no side effects, no dependencies on your project |
| **CI/CD Ready** | Exit codes and JSON output for automated quality gates in pipelines |

---

## Requirements

- **Python 3.10+**
- No external dependencies beyond `click`, `rich`, and `jinja2` (installed automatically)

---

## Installation

### From PyPI (recommended)

```bash
pip install fiops-complexity
```

### From source (for development)

```bash
# Clone the repository
git clone https://github.com/ahamedfaisal-dot/fiops.git
cd fiops

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

### Verify installation

```bash
fiopt version
```

You should see output like:
```
FiOpt v0.1.0
Python 3.12.x
Platform: ...
```

---

## Quick Start

### 1. Analyze a file from the terminal

```bash
fiopt analyze app.py
```

### 2. Analyze with verbose explanations

```bash
fiopt analyze app.py -v
```

This shows **detailed complexity breakdowns** explaining *why* each function got its Big-O rating — invaluable for learning and for AI-assisted fixes.

### 3. Analyze an entire project

```bash
fiopt analyze src/
```

FiOpt recursively discovers all `.py` files, skipping `__pycache__`, `venv`, `.git`, `node_modules`, and other common non-source directories.

### 4. Generate an HTML report

```bash
fiopt analyze src/ --format html -o report.html
```

Opens a self-contained HTML file with a visual dashboard of your codebase's health.

### 5. Get JSON output (for CI pipelines or AI assistants)

```bash
fiopt analyze app.py --format json -o results.json
```

### 6. Use as a Python library

```python
from fiopt import analyze

report = analyze("main.py")

print(report.complexity)   # e.g. "O(n²)"
print(report.bottlenecks)  # List of performance bottlenecks
print(report.suggestions)  # Optimization recommendations
print(report.summary)      # Full human-readable summary
```

---

## CLI Reference

```
fiopt analyze [OPTIONS] PATH
```

### Options

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

FiOpt exposes two primary functions for programmatic use:

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

Analyze a Python source code string directly — useful for **testing, notebooks, dynamic code, or building your own tools on top of FiOpt**.

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

### Building custom tools with the API

You can build your own analysis scripts on top of FiOpt:

```python
from fiopt import analyze
from fiopt.config import ComplexityClass

def audit_project(path: str) -> dict:
    """Generate a quality audit for your project."""
    report = analyze(path)

    critical_funcs = []
    for file_report in report.files:
        for func in file_report.function_reports:
            if func.complexity.estimated_complexity >= ComplexityClass.O_N_SQUARED:
                critical_funcs.append({
                    "file": str(file_report.filepath),
                    "function": func.name,
                    "line": func.lineno,
                    "complexity": func.complexity.estimated_complexity.value,
                    "issues": func.total_issues,
                })

    return {
        "total_files": report.total_files,
        "total_functions": report.total_functions,
        "worst_complexity": report.complexity,
        "critical_functions": critical_funcs,
        "suggestions": report.suggestions,
        "analysis_time_ms": report.analysis_duration_ms,
    }

# Use it
result = audit_project("my_project/")
print(f"Found {len(result['critical_functions'])} critical functions")
```

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

FiOpt detects these common performance anti-patterns:

| Anti-Pattern | Example | Suggestion |
|---|---|---|
| **List membership in loops** | `if x in my_list` inside a loop | Use a `set` for O(1) lookups |
| **String concatenation in loops** | `result += s` | Use `"".join()` |
| **Sorting inside loops** | `sorted()` called repeatedly | Move sort outside the loop |
| **Loop-invariant code** | Computation that doesn't change per iteration | Hoist outside the loop |
| **Unnecessary list append** | Building a list with `.append()` in a loop | Use list comprehension |

### Recursion Analysis

| Detection | Description |
|---|---|
| **Missing memoization** | Detects overlapping subproblems (e.g., naive fibonacci) |
| **Tail recursion candidates** | Functions that could be converted to iteration |
| **Missing base case** | Warns about potential infinite recursion |
| **Branching analysis** | Correctly handles mutually exclusive branches (e.g., binary search's `if/elif/else` is 1 branch, not 2) |

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

Generates a self-contained HTML report that can be shared, hosted, or included in documentation:

```bash
fiopt analyze src/ --format html -o report.html
```

The HTML report includes:
- Visual severity indicators (color-coded)
- Per-function complexity breakdown
- Collapsible details for each finding
- Project summary dashboard

### JSON

Machine-readable JSON output for CI/CD integration, custom tooling, or **feeding to AI assistants**:

```bash
# Print to stdout
fiopt analyze app.py --format json

# Save to file
fiopt analyze app.py --format json -o results.json
```

The JSON output includes full analysis details: complexity estimates, confidence scores, explanations, bottleneck lines, anti-patterns, and dead code findings.

**Pro tip for vibe coders**: Use JSON output when feeding reports to AI — it's structured and unambiguous, so your AI assistant can parse it more reliably.

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

### Full configuration options

| Option | Type | Default | Description |
|---|---|---|---|
| `complexity_warning_threshold` | `ComplexityClass` | `O(n²)` | Severity threshold for warnings |
| `complexity_critical_threshold` | `ComplexityClass` | `O(n³)` | Severity threshold for critical |
| `max_nesting_depth` | `int` | `3` | Maximum nesting depth before warning |
| `detect_dead_code` | `bool` | `True` | Enable dead code detection |
| `detect_anti_patterns` | `bool` | `True` | Enable anti-pattern detection |
| `detect_data_structure_issues` | `bool` | `True` | Enable data structure misuse detection |
| `detect_recursion_issues` | `bool` | `True` | Enable recursion analysis |
| `verbose` | `bool` | `False` | Show detailed explanations |
| `include_source` | `bool` | `True` | Include source code snippets in reports |
| `file_extensions` | `list[str]` | `[".py"]` | File types to analyze |
| `exclude_dirs` | `list[str]` | *(common dirs)* | Directories to skip |

---

## Real-World Workflows

### Vibe Coding Quality Gate

Run FiOpt after every AI-assisted coding session:

```bash
# Quick check — see if anything is critical
fiopt analyze my_project/

# Deep check — get detailed explanations to feed back to AI
fiopt analyze my_project/ -v --format json -o report.json
```

Then paste the report into your AI assistant:

> *"Here's the FiOpt analysis of our codebase. Please review and fix any functions flagged as WARNING or CRITICAL. Preserve the existing behavior while improving performance."*

### CI/CD Pipeline Integration

Add FiOpt to your GitHub Actions, GitLab CI, or any CI system:

```yaml
# .github/workflows/quality.yml
name: Code Quality Check

on: [push, pull_request]

jobs:
  complexity-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install FiOpt
        run: pip install fiops-complexity

      - name: Analyze code complexity
        run: fiopt analyze src/ --threshold "O(n²)"

      - name: Generate report artifact
        if: always()
        run: fiopt analyze src/ --format html -o complexity-report.html

      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: complexity-report
          path: complexity-report.html
```

### Pre-Commit Hook

Catch complexity issues before they're committed:

```bash
# .git/hooks/pre-commit (make executable with chmod +x)
#!/bin/sh
echo "Running FiOpt complexity check..."
fiopt analyze . --threshold "O(n²)"
if [ $? -ne 0 ]; then
    echo "FiOpt found critical complexity issues. Fix them before committing."
    exit 1
fi
echo "Complexity check passed."
```

### Jupyter Notebook Integration

Use FiOpt inside notebooks to check cells as you write:

```python
from fiopt import analyze_source

code = """
def process_data(records):
    results = []
    for record in records:
        if record['id'] not in [r['id'] for r in results]:  # O(n²)!
            results.append(record)
    return results
"""

report = analyze_source(code)
print(report.summary)
# Immediately see that this is O(n²) and get a suggestion to use a set
```

### Code Review Assistant

Write a script that reviews changed files:

```python
import subprocess
from fiopt import analyze

# Get list of changed Python files
result = subprocess.run(
    ["git", "diff", "--name-only", "HEAD~1", "--", "*.py"],
    capture_output=True, text=True
)
changed_files = result.stdout.strip().split("\n")

for filepath in changed_files:
    if filepath:
        report = analyze(filepath)
        if report.total_issues > 0:
            print(f"\n{filepath}: {report.total_issues} issues found")
            print(f"  Worst complexity: {report.complexity}")
            for suggestion in report.suggestions[:3]:
                print(f"  → {suggestion}")
```

---

## Examples

The `examples/` directory contains annotated sample files demonstrating various patterns FiOpt detects:

| File | Description | Complexity Range |
|---|---|---|
| `simple_loops.py` | Linear search, summation, constant operations | O(1) — O(n) |
| `nested_loops.py` | Bubble sort, matrix multiply, string builders | O(n²) — O(n³) |
| `recursive_functions.py` | Fibonacci, binary search, tail recursion, tree traversal | O(log n) — O(2ⁿ) |
| `data_structure_misuse.py` | List membership, string concat, sorting in loops | Anti-patterns |
| `complex_algorithm.py` | Graph algorithms — BFS, Dijkstra, PageRank | O(n) — O(n²) |

### Try them out

```bash
# See how FiOpt rates all examples with detailed explanations
fiopt analyze examples/ -v

# Analyze a specific example
fiopt analyze examples/recursive_functions.py -v

# Get JSON output for the data structure examples
fiopt analyze examples/data_structure_misuse.py --format json

# Generate a visual HTML report for the full examples suite
fiopt analyze examples/ --format html -o examples_report.html
```

### What you'll see

Running `fiopt analyze examples/recursive_functions.py -v` will show:

- `factorial` → **O(n)** — Linear recursion, single recursive call
- `fibonacci_naive` → **O(2ⁿ)** — Exponential! Missing memoization detected
- `fibonacci_memo` → **O(n)** — Memoized, properly optimized
- `binary_search_recursive` → **O(log n)** — Divide-and-conquer with halving
- `hanoi` → **O(2ⁿ)** — Branching recursion, exponential growth

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

### Design Principles

- **No code execution** — FiOpt never imports or runs your code. It's pure static analysis via Python's `ast` module.
- **Conservative estimation** — When uncertain, FiOpt reports the worst-case complexity and flags it with lower confidence.
- **Actionable output** — Every finding includes a concrete suggestion for improvement.

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

## Troubleshooting & FAQ

### Common Issues

**Q: `fiopt: command not found` after installation**

Make sure you installed FiOpt in your active Python environment:

```bash
# Check which Python is active
which python    # macOS/Linux
where python    # Windows

# Reinstall
pip install -e .

# Or run as a module
python -m fiopt.cli analyze app.py
```

**Q: FiOpt says my function is O(n²) but I think it's O(n)**

FiOpt uses conservative (worst-case) estimation. Some patterns it may flag:
- A loop containing a list membership check (`if x in my_list`) — this is O(n) per check, making the loop O(n²)
- A loop calling a function that itself contains a loop
- Use `-v` (verbose) to see the detailed reasoning

**Q: Can FiOpt analyze files other than Python?**

Currently, FiOpt only supports Python (`.py`) files. Support for other languages may be added in future versions.

**Q: Does FiOpt execute my code?**

**No.** FiOpt is a pure static analysis tool. It parses your code into an AST (Abstract Syntax Tree) and analyzes the structure. Your code is never imported, executed, or evaluated.

**Q: How accurate is the complexity estimation?**

FiOpt uses heuristic-based analysis, which is accurate for common patterns (loops, recursion, known stdlib calls). It may not be able to determine complexity for:
- Algorithms with input-dependent control flow
- External library calls with unknown complexity
- Amortized complexity (e.g., dynamic arrays)

In such cases, it reports `Unknown` or flags the function for manual review.

**Q: Can I use FiOpt in my own tools/scripts?**

Yes! FiOpt's Python API (`analyze()` and `analyze_source()`) is designed for programmatic use. See the [Python API](#python-api) section for details.

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Setting up your development environment
- Running the test suite
- Coding style and standards
- Creating pull requests

Please also review our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## License

[MIT](LICENSE) © 2026 Ahamed Faisal

---

<p align="center">
  <b>FiOpt</b> — Stop shipping slow code. Let the tools catch what you miss.<br>
  <sub>Built for the vibe coding community</sub>
</p>
