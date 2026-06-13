"""Tests for the CLI."""

import pytest
from click.testing import CliRunner
from fiopt.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestCLI:
    def test_version_command(self, runner):
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert "FiOpt" in result.output

    def test_analyze_file(self, runner, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def bubble_sort(arr):
    for i in range(len(arr)):
        for j in range(len(arr) - 1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
""")
        result = runner.invoke(main, ["analyze", str(test_file)])
        # Should run without crashing
        assert result.exit_code in (0, 1)  # 1 is ok for critical issues

    def test_analyze_json_format(self, runner, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def add(a, b):
    return a + b
""")
        result = runner.invoke(main, ["analyze", str(test_file), "--format", "json"])
        assert result.exit_code == 0
        assert '"fiopt_version"' in result.output

    def test_analyze_html_format(self, runner, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): return 1")
        output_file = tmp_path / "report.html"
        result = runner.invoke(
            main, ["analyze", str(test_file), "--format", "html", "-o", str(output_file)]
        )
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "FiOpt" in content

    def test_analyze_nonexistent_file(self, runner):
        result = runner.invoke(main, ["analyze", "nonexistent.py"])
        assert result.exit_code != 0

    def test_analyze_directory(self, runner, tmp_path):
        f1 = tmp_path / "a.py"
        f1.write_text("def a(): return 1")
        f2 = tmp_path / "b.py"
        f2.write_text("def b(): return 2")
        result = runner.invoke(main, ["analyze", str(tmp_path)])
        assert result.exit_code == 0

    def test_verbose_flag(self, runner, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def loop(arr):
    for x in arr:
        print(x)
""")
        result = runner.invoke(main, ["analyze", str(test_file), "-v"])
        assert result.exit_code == 0
