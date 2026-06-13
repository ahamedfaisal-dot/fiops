"""Tests for the AST parser module."""

import ast
import pytest
from fiopt.parser.ast_parser import parse, FunctionInfo, ClassInfo


class TestParse:
    def test_parse_simple_function(self, simple_function_source):
        result = parse(simple_function_source)
        assert len(result.functions) == 1
        assert result.functions[0].name == "add"
        assert result.functions[0].args == ["a", "b"]

    def test_parse_class(self):
        source = """
class MyClass:
    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value
"""
        result = parse(source)
        assert len(result.classes) == 1
        assert result.classes[0].name == "MyClass"
        assert len(result.classes[0].methods) == 2
        assert result.classes[0].methods[0].name == "__init__"
        assert result.classes[0].methods[0].is_method is True

    def test_parse_async_function(self):
        source = """
async def fetch_data(url):
    pass
"""
        result = parse(source)
        assert len(result.functions) == 1
        assert result.functions[0].is_async is True

    def test_parse_decorated_function(self):
        source = """
@staticmethod
def helper():
    pass
"""
        result = parse(source)
        assert "staticmethod" in result.functions[0].decorators

    def test_parse_docstring(self):
        source = '''
def documented():
    """This is the docstring."""
    return 42
'''
        result = parse(source)
        assert result.functions[0].docstring == "This is the docstring."

    def test_parse_imports(self):
        source = """
import os
from pathlib import Path
import sys as system
"""
        result = parse(source)
        assert len(result.imports) == 3

    def test_parse_global_variables(self):
        source = """
MAX_SIZE = 100
name = "test"
x, y = 1, 2
"""
        result = parse(source)
        assert "MAX_SIZE" in result.global_variables
        assert "name" in result.global_variables

    def test_parse_generator(self):
        source = """
def gen():
    yield 1
    yield 2
"""
        result = parse(source)
        assert result.functions[0].is_generator is True

    def test_all_functions_includes_methods(self):
        source = """
def standalone():
    pass

class Foo:
    def method(self):
        pass
"""
        result = parse(source)
        all_funcs = result.all_functions
        names = [f.name for f in all_funcs]
        assert "standalone" in names
        assert "method" in names

    def test_parse_syntax_error(self):
        with pytest.raises(SyntaxError):
            parse("def broken(:")

    def test_parse_nested_functions(self):
        source = """
def outer():
    def inner():
        pass
    return inner
"""
        result = parse(source)
        assert result.functions[0].nested_functions == ["inner"]
