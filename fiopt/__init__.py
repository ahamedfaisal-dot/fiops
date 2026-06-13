"""FiOpt — AI-Powered Code Complexity & Optimization Engine.

FiOpt is a compiler-inspired optimization platform for Python codebases.
It combines static analysis, runtime profiling, AI reasoning, and automatic
code transformation to analyze algorithmic complexity, detect bottlenecks,
and suggest optimized alternatives.

Quick Start:
    >>> from fiopt import analyze
    >>> report = analyze("main.py")
    >>> print(report.summary)
"""

from fiopt.api import analyze, analyze_source

__version__ = "0.1.0"
__all__ = ["analyze", "analyze_source", "__version__"]
