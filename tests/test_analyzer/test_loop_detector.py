"""Tests for loop detection."""

import ast
import pytest
from fiopt.analyzer.loop_detector import detect_loops, LoopKind


def _get_func_node(source: str) -> ast.FunctionDef:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            return node
    raise ValueError("No function found")


class TestLoopDetector:
    def test_detect_for_loop(self, linear_loop_source):
        func = _get_func_node(linear_loop_source)
        analysis = detect_loops(func)
        assert analysis.total_loops == 1
        assert analysis.loops[0].kind == LoopKind.FOR
        assert analysis.loops[0].depth == 1

    def test_detect_nested_loops(self, nested_loop_source):
        func = _get_func_node(nested_loop_source)
        analysis = detect_loops(func)
        assert analysis.total_loops == 2
        assert analysis.max_depth == 2

    def test_detect_while_loop(self, binary_search_source):
        func = _get_func_node(binary_search_source)
        analysis = detect_loops(func)
        assert analysis.total_loops == 1
        assert analysis.loops[0].kind == LoopKind.WHILE

    def test_detect_triple_nesting(self, triple_nested_source):
        func = _get_func_node(triple_nested_source)
        analysis = detect_loops(func)
        assert analysis.max_depth == 3

    def test_detect_list_comprehension(self):
        source = """
def comp(data):
    return [x * 2 for x in data]
"""
        func = _get_func_node(source)
        analysis = detect_loops(func)
        assert analysis.total_loops == 1
        assert analysis.loops[0].kind == LoopKind.LIST_COMP

    def test_loop_variables(self, linear_loop_source):
        func = _get_func_node(linear_loop_source)
        analysis = detect_loops(func)
        assert len(analysis.loops[0].variables) == 1
        assert analysis.loops[0].variables[0].name == "item"

    def test_no_loops(self, simple_function_source):
        func = _get_func_node(simple_function_source)
        analysis = detect_loops(func)
        assert analysis.total_loops == 0
        assert analysis.max_depth == 0

    def test_sorting_in_loop_detected(self):
        source = """
def bad(data, queries):
    for q in queries:
        s = sorted(data)
"""
        func = _get_func_node(source)
        analysis = detect_loops(func)
        assert analysis.loops[0].has_expensive_operation is True

    def test_parent_child_relationship(self, nested_loop_source):
        func = _get_func_node(nested_loop_source)
        analysis = detect_loops(func)
        outer = [l for l in analysis.loops if l.depth == 1][0]
        inner = [l for l in analysis.loops if l.depth == 2][0]
        assert inner.parent is outer
        assert inner in outer.children
