"""Tests for the public API."""

import pytest
from fiopt import analyze, analyze_source
from fiopt.config import ComplexityClass


class TestAnalyzeSource:
    def test_analyze_simple(self):
        report = analyze_source("""
def add(a, b):
    return a + b
""")
        assert report.total_functions == 1
        assert report.worst_complexity == ComplexityClass.O_1

    def test_analyze_nested_loops(self):
        report = analyze_source("""
def sort(arr):
    for i in range(len(arr)):
        for j in range(len(arr)):
            if arr[i] > arr[j]:
                arr[i], arr[j] = arr[j], arr[i]
""")
        assert report.worst_complexity == ComplexityClass.O_N_SQUARED

    def test_report_has_summary(self):
        report = analyze_source("def foo(): return 1")
        assert report.summary
        assert "FiOpt" in report.summary

    def test_report_bottlenecks(self):
        report = analyze_source("""
def quadratic(data):
    for i in range(len(data)):
        for j in range(len(data)):
            pass
""")
        assert len(report.bottlenecks) >= 1

    def test_report_suggestions(self):
        report = analyze_source("""
def check(items, lst):
    allowed = list(lst)
    for item in items:
        if item in allowed:
            pass
""")
        # Should suggest using a set
        assert len(report.suggestions) >= 1

    def test_analyze_file(self, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): return 1")
        report = analyze(str(test_file))
        assert report.total_files == 1
        assert report.total_functions == 1

    def test_analyze_directory(self, tmp_path):
        (tmp_path / "a.py").write_text("def a(): pass")
        (tmp_path / "b.py").write_text("def b(): pass")
        report = analyze(str(tmp_path))
        assert report.total_files == 2

    def test_analysis_duration(self):
        report = analyze_source("def foo(): return 1")
        assert report.analysis_duration_ms > 0

    def test_complexity_property(self):
        report = analyze_source("""
def quadratic(data):
    for i in data:
        for j in data:
            pass
""")
        assert report.complexity == "O(n²)"
