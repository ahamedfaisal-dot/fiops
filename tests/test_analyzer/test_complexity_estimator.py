"""Tests for the complexity estimator — the most critical component."""

import ast
import pytest
from fiopt.config import ComplexityClass
from fiopt.analyzer.complexity_estimator import estimate_complexity


def _get_func_node(source: str) -> ast.FunctionDef:
    """Helper to extract the first function from source."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    raise ValueError("No function found in source")


def _get_all_func_nodes(source: str) -> dict[str, ast.FunctionDef]:
    """Helper to get all function nodes from source."""
    tree = ast.parse(source)
    funcs = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs[node.name] = node
    return funcs


class TestComplexityO1:
    """Test O(1) complexity detection."""

    def test_constant_arithmetic(self):
        source = """
def add(a, b):
    return a + b
"""
        result = estimate_complexity(_get_func_node(source))
        assert result.estimated_complexity == ComplexityClass.O_1

    def test_constant_operations(self):
        source = """
def compute(x, y, z):
    a = x * y
    b = a + z
    c = b ** 2
    return c
"""
        result = estimate_complexity(_get_func_node(source))
        assert result.estimated_complexity == ComplexityClass.O_1

    def test_fixed_loop(self):
        source = """
def fixed():
    total = 0
    for i in range(10):
        total += i
    return total
"""
        result = estimate_complexity(_get_func_node(source))
        assert result.estimated_complexity == ComplexityClass.O_1

    def test_dictionary_lookup(self):
        source = """
def lookup(d, key):
    return d.get(key, None)
"""
        result = estimate_complexity(_get_func_node(source))
        assert result.estimated_complexity == ComplexityClass.O_1


class TestComplexityON:
    """Test O(n) complexity detection."""

    def test_single_for_loop(self):
        source = """
def linear(arr):
    total = 0
    for x in arr:
        total += x
    return total
"""
        result = estimate_complexity(_get_func_node(source))
        assert result.estimated_complexity == ComplexityClass.O_N

    def test_range_n_loop(self):
        source = """
def linear(n):
    total = 0
    for i in range(n):
        total += i
    return total
"""
        result = estimate_complexity(_get_func_node(source))
        assert result.estimated_complexity == ComplexityClass.O_N

    def test_while_loop_linear(self):
        source = """
def linear(n):
    i = 0
    while i < n:
        i += 1
"""
        result = estimate_complexity(_get_func_node(source))
        assert result.estimated_complexity == ComplexityClass.O_N


class TestComplexityOLogN:
    """Test O(log n) complexity detection."""

    def test_binary_search(self, binary_search_source):
        result = estimate_complexity(_get_func_node(binary_search_source))
        assert result.estimated_complexity == ComplexityClass.O_LOG_N

    def test_halving_pattern(self):
        source = """
def halve(n):
    while n > 1:
        n = n // 2
"""
        result = estimate_complexity(_get_func_node(source))
        assert result.estimated_complexity == ComplexityClass.O_LOG_N


class TestComplexityONSquared:
    """Test O(n²) complexity detection."""

    def test_nested_loops(self, nested_loop_source):
        result = estimate_complexity(_get_func_node(nested_loop_source))
        assert result.estimated_complexity == ComplexityClass.O_N_SQUARED

    def test_bubble_sort(self):
        source = """
def sort(arr):
    for i in range(len(arr)):
        for j in range(len(arr) - 1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
"""
        result = estimate_complexity(_get_func_node(source))
        assert result.estimated_complexity == ComplexityClass.O_N_SQUARED

    def test_all_pairs(self):
        source = """
def pairs(items):
    result = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            result.append((items[i], items[j]))
    return result
"""
        result = estimate_complexity(_get_func_node(source))
        assert result.estimated_complexity == ComplexityClass.O_N_SQUARED


class TestComplexityONCubed:
    """Test O(n³) complexity detection."""

    def test_triple_nested(self, triple_nested_source):
        result = estimate_complexity(_get_func_node(triple_nested_source))
        assert result.estimated_complexity == ComplexityClass.O_N_CUBED

    def test_matrix_multiply(self):
        source = """
def multiply(a, b):
    n = len(a)
    result = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                result[i][j] += a[i][k] * b[k][j]
    return result
"""
        result = estimate_complexity(_get_func_node(source))
        assert result.estimated_complexity == ComplexityClass.O_N_CUBED


class TestComplexityRecursion:
    """Test recursion complexity detection."""

    def test_fibonacci_exponential(self, recursive_source):
        source = recursive_source
        func_node = _get_func_node(source)
        result = estimate_complexity(
            func_node,
            all_function_names={"fibonacci"},
        )
        assert result.estimated_complexity == ComplexityClass.O_2_N

    def test_linear_recursion(self):
        source = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        func_node = _get_func_node(source)
        result = estimate_complexity(
            func_node,
            all_function_names={"factorial"},
        )
        assert result.estimated_complexity == ComplexityClass.O_N

    def test_recursive_binary_search(self):
        source = """
def bsearch(arr, target, low, high):
    if low > high:
        return -1
    mid = (low + high) // 2
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        return bsearch(arr, target, mid + 1, high)
    else:
        return bsearch(arr, target, low, mid - 1)
"""
        func_node = _get_func_node(source)
        result = estimate_complexity(
            func_node,
            all_function_names={"bsearch"},
        )
        assert result.estimated_complexity == ComplexityClass.O_LOG_N


class TestComplexityNLogN:
    """Test O(n log n) detection."""

    def test_sorted_call(self):
        source = """
def sort_data(arr):
    return sorted(arr)
"""
        result = estimate_complexity(_get_func_node(source))
        assert result.estimated_complexity == ComplexityClass.O_N_LOG_N


class TestComplexityExplanations:
    """Test that explanations are generated."""

    def test_has_explanations(self, nested_loop_source):
        result = estimate_complexity(_get_func_node(nested_loop_source))
        assert len(result.explanations) > 0

    def test_has_bottleneck(self, nested_loop_source):
        result = estimate_complexity(_get_func_node(nested_loop_source))
        assert result.bottleneck_lines

    def test_memoization_warning(self, recursive_source):
        func_node = _get_func_node(recursive_source)
        result = estimate_complexity(
            func_node,
            all_function_names={"fibonacci"},
        )
        assert any("memoiz" in w.lower() for w in result.warnings)

    def test_confidence_simple(self):
        source = """
def simple(x):
    return x + 1
"""
        result = estimate_complexity(_get_func_node(source))
        assert result.confidence >= 0.9

    def test_confidence_recursive(self, recursive_source):
        func_node = _get_func_node(recursive_source)
        result = estimate_complexity(
            func_node,
            all_function_names={"fibonacci"},
        )
        assert result.confidence < 0.9  # Less confident for recursion
