"""Nested loop examples for FiOpt testing.

Contains O(n²), O(n³) patterns and anti-patterns.
"""


def bubble_sort(arr):
    """O(n²) — classic bubble sort with nested loops."""
    n = len(arr)
    for i in range(n):
        for j in range(n - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr


def find_duplicates_naive(arr):
    """O(n²) — check every pair for duplicates."""
    duplicates = []
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            if arr[i] == arr[j] and arr[i] not in duplicates:
                duplicates.append(arr[i])
    return duplicates


def matrix_multiply(a, b):
    """O(n³) — standard matrix multiplication."""
    n = len(a)
    result = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                result[i][j] += a[i][k] * b[k][j]
    return result


def has_common_element(list1, list2):
    """O(n²) — but could be O(n) with sets."""
    for item in list1:
        if item in list2:  # O(n) membership on list
            return True
    return False


def sort_and_search_in_loop(data, queries):
    """O(n² log n) — sorting inside a loop (anti-pattern)."""
    results = []
    for q in queries:
        sorted_data = sorted(data)  # O(n log n) INSIDE loop!
        idx = binary_search(sorted_data, q)
        results.append(idx)
    return results


def binary_search(arr, target):
    """O(log n) — binary search with halving pattern."""
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


def string_builder_bad(items):
    """O(n²) — string concatenation in loop (anti-pattern)."""
    result = ""
    for item in items:
        result += str(item) + ", "  # Creates new string each time!
    return result


def string_builder_good(items):
    """O(n) — proper string building."""
    parts = []
    for item in items:
        parts.append(str(item))
    return ", ".join(parts)
