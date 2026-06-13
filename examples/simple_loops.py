"""Simple loop examples for FiOpt testing.

Contains O(n) and O(1) patterns.
"""


def linear_search(arr, target):
    """O(n) — simple linear scan."""
    for item in arr:
        if item == target:
            return True
    return False


def sum_list(arr):
    """O(n) — iterate and accumulate."""
    total = 0
    for x in arr:
        total += x
    return total


def find_max(arr):
    """O(n) — single pass to find maximum."""
    if not arr:
        return None
    max_val = arr[0]
    for x in arr[1:]:
        if x > max_val:
            max_val = x
    return max_val


def count_occurrences(arr, target):
    """O(n) — count how many times target appears."""
    count = 0
    for item in arr:
        if item == target:
            count += 1
    return count


def constant_operation(x, y):
    """O(1) — no loops, just arithmetic."""
    return (x + y) * (x - y)


def fixed_iterations():
    """O(1) — loop with constant bound."""
    total = 0
    for i in range(10):
        total += i
    return total
