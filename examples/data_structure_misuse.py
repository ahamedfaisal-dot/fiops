"""Data structure misuse examples for FiOpt testing.

Contains common anti-patterns related to data structure choices.
"""
import json


def find_common_elements_bad(list1, list2):
    """Using list for membership checking — should use set."""
    common = []
    seen = list(list1)  # This is a list!
    for item in list2:
        if item in seen:  # O(n) per check!
            common.append(item)
    return common


def find_common_elements_good(list1, list2):
    """Using set for membership checking — correct approach."""
    seen = set(list1)  # O(1) lookups
    common = []
    for item in list2:
        if item in seen:  # O(1)!
            common.append(item)
    return common


def process_queue_bad(items):
    """Using list.pop(0) as a queue — should use deque."""
    queue = list(items)
    results = []
    while queue:
        item = queue.pop(0)  # O(n) — shifts all elements!
        results.append(item * 2)
    return results


def build_index_bad(records):
    """Manual dict key checking — should use setdefault/defaultdict."""
    index = dict()
    for record in records:
        key = record["category"]
        if key not in index:  # Manual check pattern
            index[key] = []
        index[key].append(record)
    return index


def concatenate_strings_bad(words):
    """String concatenation in a loop — O(n²) memory."""
    result = ""
    for word in words:
        result += word + " "  # New string allocation each time!
    return result.strip()


def repeated_sort(data, thresholds):
    """Sorting inside a loop when data doesn't change."""
    results = []
    for threshold in thresholds:
        sorted_data = sorted(data)  # Redundant sort each iteration!
        count = sum(1 for x in sorted_data if x > threshold)
        results.append(count)
    return results


def membership_check_list_literal(value):
    """Membership check against a list literal — should be set."""
    valid_statuses = ["active", "pending", "review", "approved", "rejected"]
    return value in valid_statuses


def process_with_io_in_loop(filenames):
    """I/O operation inside a loop."""
    results = []
    for fname in filenames:
        with open(fname) as f:  # I/O in loop
            data = json.loads(f.read())
            results.append(data)
    return results


def unused_variable_example(data):
    """Contains unused variables and dead code."""
    temp = data[0]  # unused variable
    result = []
    for item in data:
        if item > 0:
            result.append(item)
            return result  # returns early
            print("unreachable")  # dead code!
    return result
