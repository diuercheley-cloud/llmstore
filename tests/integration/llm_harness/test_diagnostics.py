from scripts.llm_harness.diagnostics import (
    diagnose_errors,
    parse_csharp_dotnet_test,
    parse_java_stacktrace,
    parse_mypy_output,
    parse_npm_tsc_output,
    parse_pytest_failure,
    parse_python_traceback,
    parse_ruff_output,
)


def test_parse_python_traceback():
    trace = """Traceback (most recent call last):
  File "scripts/llm_harness/cli.py", line 254, in main
    HarnessConfig.load_config(getattr(args, "config", None))
ZeroDivisionError: division by zero
"""
    diagnostics = parse_python_traceback(trace)
    assert len(diagnostics) == 1
    d = diagnostics[0]
    assert d.file == "scripts/llm_harness/cli.py"
    assert d.line == 254
    assert d.severity == "error"
    assert "ZeroDivisionError" in d.message
    assert "ZeroDivisionError" in d.raw_excerpt or "line 254" in d.raw_excerpt


def test_parse_pytest_failure():
    pytest_out = """
=================================== FAILURES ===================================
___________________ test_repository_indexer_and_ignore_rules ___________________
tests/integration/llm_harness/test_indexing.py:217: AssertionError: Some assertion message here
"""
    diagnostics = parse_pytest_failure(pytest_out)
    assert len(diagnostics) == 1
    d = diagnostics[0]
    assert d.file == "tests/integration/llm_harness/test_indexing.py"
    assert d.line == 217
    assert d.severity == "error"
    assert "AssertionError" in d.message
    assert "Some assertion message here" in d.message


def test_parse_ruff_and_mypy_output():
    ruff_out = "scripts/llm_harness/cli.py:1:1: I001 [*] Import block is un-sorted or un-formatted"
    mypy_out = (
        "scripts/llm_harness/indexing/symbol_index.py:13: "
        'error: Need type annotation for "classes"'
    )

    ruff_diagnostics = parse_ruff_output(ruff_out)
    assert len(ruff_diagnostics) == 1
    rd = ruff_diagnostics[0]
    assert rd.file == "scripts/llm_harness/cli.py"
    assert rd.line == 1
    assert rd.severity == "warning"  # I001 is a warning in ruff check
    assert "Import block is un-sorted" in rd.message

    mypy_diagnostics = parse_mypy_output(mypy_out)
    assert len(mypy_diagnostics) == 1
    md = mypy_diagnostics[0]
    assert md.file == "scripts/llm_harness/indexing/symbol_index.py"
    assert md.line == 13
    assert md.severity == "error"
    assert "Need type annotation" in md.message


def test_parse_typescript_java_and_csharp_output():
    ts_out = "src/app.ts(12,4): error TS2322: Type 'string' is not assignable to type 'number'."
    java_out = """
Exception in thread "main" java.lang.NullPointerException
    at com.example.App.run(App.java:42)
"""
    csharp_out = "   at MyApp.Tests.SampleTests.Fails() in /tmp/SampleTests.cs:line 17"

    ts_diagnostics = parse_npm_tsc_output(ts_out)
    assert len(ts_diagnostics) == 1
    assert ts_diagnostics[0].file == "src/app.ts"
    assert ts_diagnostics[0].line == 12
    assert "TS2322" in ts_diagnostics[0].message

    java_diagnostics = parse_java_stacktrace(java_out)
    assert len(java_diagnostics) == 1
    assert java_diagnostics[0].file == "App.java"
    assert java_diagnostics[0].line == 42

    csharp_diagnostics = parse_csharp_dotnet_test(csharp_out)
    assert len(csharp_diagnostics) == 1
    assert csharp_diagnostics[0].file == "/tmp/SampleTests.cs"
    assert csharp_diagnostics[0].line == 17


def test_diagnostics_redacts_secrets():
    trace = """Traceback (most recent call last):
  File "scripts/llm_harness/cli.py", line 254, in main
    HarnessConfig.load_config(getattr(args, "config", None))
ValueError: Invalid api_key=bearer-test-token
"""
    diagnostics = diagnose_errors(trace)
    assert len(diagnostics) > 0
    # None of the diagnostics must leak the secret key
    for d in diagnostics:
        assert "bearer-test-token" not in d.message
        assert "bearer-test-token" not in d.raw_excerpt
        assert "[REDACTED]" in d.message or "[REDACTED]" in d.raw_excerpt
