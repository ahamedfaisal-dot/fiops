"""Tests for recursion detection."""

import ast
import pytest
from fiopt.analyzer.recursion_detector import detect_recursion


def _get_func_node(source: str) -> ast.FunctionDef:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            return node
    raise ValueError("No function found")


class TestRecursionDetector:
    def test_detect_direct_recursion(self, recursive_source):
        func = _get_func_node(recursive_source)
        result = detect_recursion(func, {"fibonacci"})
        assert result.is_recursive is True
        assert len(result.direct_calls) >= 1

    def test_non_recursive(self, simple_function_source):
        func = _get_func_node(simple_function_source)
        result = detect_recursion(func)
        assert result.is_recursive is False

    def test_detect_base_case(self, recursive_source):
        func = _get_func_node(recursive_source)
        result = detect_recursion(func, {"fibonacci"})
        assert result.has_base_case is True

    def test_detect_memoization_opportunity(self, recursive_source):
        func = _get_func_node(recursive_source)
        result = detect_recursion(func, {"fibonacci"})
        assert result.can_be_memoized is True

    def test_detect_tail_recursion(self):
        source = """
def tail_sum(n, acc=0):
    if n <= 0:
        return acc
    return tail_sum(n - 1, acc + n)
"""
        func = _get_func_node(source)
        result = detect_recursion(func, {"tail_sum"})
        assert result.is_tail_recursive is True

    def test_linear_recursion_single_branch(self):
        source = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        func = _get_func_node(source)
        result = detect_recursion(func, {"factorial"})
        assert result.estimated_branches == 1
        assert result.depth_pattern == "linear"

    def test_exponential_recursion(self, recursive_source):
        func = _get_func_node(recursive_source)
        result = detect_recursion(func, {"fibonacci"})
        assert result.estimated_branches >= 2
        assert result.has_overlapping_subproblems is True
