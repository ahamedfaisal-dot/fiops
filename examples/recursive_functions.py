"""Recursive function examples for FiOpt testing.

Contains various recursion patterns with different complexities.
"""


def factorial(n):
    """O(n) — simple linear recursion."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)


def fibonacci_naive(n):
    """O(2^n) — exponential recursion with overlapping subproblems.

    This is the classic example of where memoization is needed.
    """
    if n <= 1:
        return n
    return fibonacci_naive(n - 1) + fibonacci_naive(n - 2)


def fibonacci_memo(n, memo=None):
    """O(n) — memoized fibonacci."""
    if memo is None:
        memo = {}
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fibonacci_memo(n - 1, memo) + fibonacci_memo(n - 2, memo)
    return memo[n]


def binary_search_recursive(arr, target, low=0, high=None):
    """O(log n) — recursive binary search."""
    if high is None:
        high = len(arr) - 1
    if low > high:
        return -1
    mid = (low + high) // 2
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        return binary_search_recursive(arr, target, mid + 1, high)
    else:
        return binary_search_recursive(arr, target, low, mid - 1)


def power(base, exp):
    """O(log n) — fast exponentiation by squaring."""
    if exp == 0:
        return 1
    if exp % 2 == 0:
        half = power(base, exp // 2)
        return half * half
    return base * power(base, exp - 1)


def tree_sum(node):
    """O(n) — traverse entire tree."""
    if node is None:
        return 0
    return node.value + tree_sum(node.left) + tree_sum(node.right)


def flatten_list(nested):
    """O(n) — flatten a nested list structure."""
    result = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result


def hanoi(n, source, target, auxiliary):
    """O(2^n) — Tower of Hanoi."""
    if n == 1:
        print(f"Move disk 1 from {source} to {target}")
        return
    hanoi(n - 1, source, auxiliary, target)
    print(f"Move disk {n} from {source} to {target}")
    hanoi(n - 1, auxiliary, target, source)


def tail_recursive_sum(n, accumulator=0):
    """O(n) — tail recursive (candidate for optimization)."""
    if n <= 0:
        return accumulator
    return tail_recursive_sum(n - 1, accumulator + n)
