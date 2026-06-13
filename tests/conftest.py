"""Shared test fixtures for FiOpt tests."""

import ast
import pytest


@pytest.fixture
def simple_function_source():
    """A simple O(1) function."""
    return """
def add(a, b):
    return a + b
"""


@pytest.fixture
def linear_loop_source():
    """An O(n) function with a single loop."""
    return """
def find(arr, target):
    for item in arr:
        if item == target:
            return True
    return False
"""


@pytest.fixture
def nested_loop_source():
    """An O(n²) function with nested loops."""
    return """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(n - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
"""


@pytest.fixture
def triple_nested_source():
    """An O(n³) function with triple nested loops."""
    return """
def matrix_multiply(a, b):
    n = len(a)
    result = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                result[i][j] += a[i][k] * b[k][j]
    return result
"""


@pytest.fixture
def recursive_source():
    """A recursive function (fibonacci — O(2^n))."""
    return """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
"""


@pytest.fixture
def binary_search_source():
    """An O(log n) binary search."""
    return """
def binary_search(arr, target):
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
"""


@pytest.fixture
def list_membership_source():
    """Function with list membership anti-pattern."""
    return """
def check_items(items, allowed):
    allowed_list = list(allowed)
    result = []
    for item in items:
        if item in allowed_list:
            result.append(item)
    return result
"""


@pytest.fixture
def string_concat_source():
    """Function with string concatenation in loop."""
    return """
def build_string(items):
    result = ""
    for item in items:
        result += str(item) + ", "
    return result
"""


@pytest.fixture
def dead_code_source():
    """Function with unreachable code."""
    return """
def process(data):
    for item in data:
        if item > 0:
            return item
            print("unreachable")
    return None
"""


@pytest.fixture
def parse_tree(simple_function_source):
    """Pre-parsed AST tree."""
    return ast.parse(simple_function_source)
