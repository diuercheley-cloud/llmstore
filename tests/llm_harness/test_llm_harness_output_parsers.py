from scripts.llm_harness.output_parsers import (
    parse_mypy_output,
    parse_pytest_output,
    parse_ruff_output,
)


def test_pytest_parser_identifies_failures():
    output = """
FAILED tests/test_demo.py::test_nope - AssertionError: expected 2
=========================== short test summary info ============================
FAILED tests/test_demo.py::test_nope - AssertionError: expected 2
"""
    parsed = parse_pytest_output(output, 1)
    assert parsed.kind == "pytest"
    assert parsed.error_count >= 1
    assert parsed.failures[0].location == "tests/test_demo.py::test_nope"


def test_ruff_parser_identifies_errors():
    output = "app.py:10:5: F401 `os` imported but unused"
    parsed = parse_ruff_output(output, 1)
    assert parsed.kind == "ruff"
    assert parsed.error_count == 1
    assert parsed.failures[0].location == "app.py:10:5"


def test_mypy_parser_identifies_errors():
    output = "main.py:12: error: Incompatible return value type (got \"int\", expected \"str\")"
    parsed = parse_mypy_output(output, 1)
    assert parsed.kind == "mypy"
    assert parsed.error_count == 1
    assert parsed.failures[0].location == "main.py:12"
