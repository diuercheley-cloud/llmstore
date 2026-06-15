import re
from typing import Any

from pydantic import BaseModel

from .sanitizer import Sanitizer


class Diagnostic(BaseModel):
    file: str | None = None
    line: int | None = None
    severity: str = "error"  # error, warning, info
    message: str
    suggested_action: str | None = None
    raw_excerpt: str | None = None


def parse_python_traceback(output: str) -> list[Diagnostic]:
    diagnostics = []
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if 'File "' in line and '", line ' in line:
            m = re.search(r'File "([^"]+)", line (\d+)', line)
            if m:
                filepath = m.group(1)
                lineno = int(m.group(2))
                err_msg = "Python traceback error"
                raw_exc = line
                # Look ahead for exception name and message
                for j in range(i + 1, min(i + 5, len(lines))):
                    if re.match(r"^[a-zA-Z0-9._]+Error:", lines[j]) or re.match(
                        r"^[a-zA-Z0-9._]+Exception:", lines[j]
                    ):
                        err_msg = lines[j]
                        break
                diagnostics.append(
                    Diagnostic(
                        file=filepath,
                        line=lineno,
                        severity="error",
                        message=Sanitizer.sanitize_text(err_msg),
                        suggested_action=(
                            f"Check syntax or logic around line {lineno} in {filepath}."
                        ),
                        raw_excerpt=Sanitizer.sanitize_text(raw_exc),
                    )
                )
    return diagnostics


def parse_pytest_failure(output: str) -> list[Diagnostic]:
    diagnostics = []
    lines = output.splitlines()
    for line in lines:
        m = re.match(
            r"^([a-zA-Z0-9_\-\.\/]+):(\d+):\s*([a-zA-Z0-9._]+Error|AssertionError)(?::\s*(.*))?$",
            line,
        )
        if m:
            filepath = m.group(1)
            lineno = int(m.group(2))
            exc_type = m.group(3)
            message = m.group(4) or exc_type
            diagnostics.append(
                Diagnostic(
                    file=filepath,
                    line=lineno,
                    severity="error",
                    message=Sanitizer.sanitize_text(f"{exc_type}: {message}"),
                    suggested_action=(
                        f"Fix assertion or test failure at line {lineno} in {filepath}."
                    ),
                    raw_excerpt=Sanitizer.sanitize_text(line),
                )
            )
    return diagnostics


def parse_ruff_output(output: str) -> list[Diagnostic]:
    diagnostics = []
    lines = output.splitlines()
    for line in lines:
        m = re.match(r"^([^:]+):(\d+):(\d+):\s*([A-Z0-9]+)\s*(.*)$", line)
        if m:
            filepath = m.group(1)
            lineno = int(m.group(2))
            rule_id = m.group(4)
            message = m.group(5)
            diagnostics.append(
                Diagnostic(
                    file=filepath,
                    line=lineno,
                    severity=(
                        "error" if rule_id.startswith("E") or rule_id.startswith("F") else "warning"
                    ),
                    message=Sanitizer.sanitize_text(f"Ruff {rule_id}: {message}"),
                    suggested_action=f"Resolve ruff linter issue {rule_id} at line {lineno}.",
                    raw_excerpt=Sanitizer.sanitize_text(line),
                )
            )
    return diagnostics


def parse_mypy_output(output: str) -> list[Diagnostic]:
    diagnostics = []
    lines = output.splitlines()
    for line in lines:
        m = re.match(r"^([^:]+):(\d+):\s*(error|warning|note):\s*(.*)$", line)
        if m:
            filepath = m.group(1)
            lineno = int(m.group(2))
            severity = m.group(3)
            message = m.group(4)
            diagnostics.append(
                Diagnostic(
                    file=filepath,
                    line=lineno,
                    severity=severity,
                    message=Sanitizer.sanitize_text(message),
                    suggested_action=(
                        f"Fix mypy type error: {message} at line {lineno} in {filepath}."
                    ),
                    raw_excerpt=Sanitizer.sanitize_text(line),
                )
            )
    return diagnostics


def parse_npm_tsc_output(output: str) -> list[Diagnostic]:
    diagnostics = []
    lines = output.splitlines()
    for line in lines:
        m = re.match(r"^([^(]+)\((\d+),(\d+)\):\s*(error|warning)\s+(TS\d+):\s*(.*)$", line)
        if m:
            filepath = m.group(1)
            lineno = int(m.group(2))
            tsc_code = m.group(5)
            message = m.group(6)
            diagnostics.append(
                Diagnostic(
                    file=filepath,
                    line=lineno,
                    severity="error",
                    message=Sanitizer.sanitize_text(f"TypeScript {tsc_code}: {message}"),
                    suggested_action=f"Resolve TypeScript error {tsc_code} at line {lineno}.",
                    raw_excerpt=Sanitizer.sanitize_text(line),
                )
            )
    return diagnostics


def parse_java_stacktrace(output: str) -> list[Diagnostic]:
    diagnostics = []
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if "at " in line and ".java:" in line:
            m = re.search(
                r"at\s+([a-zA-Z0-9._$]+)\.([a-zA-Z0-9_<>$]+)\(([^:]+)\.java:(\d+)\)",
                line,
            )
            if m:
                class_name = m.group(1)
                filename = m.group(3) + ".java"
                lineno = int(m.group(4))
                message = "Java Exception"
                for j in range(max(0, i - 5), i + 1):
                    if "Exception" in lines[j] or "Error" in lines[j]:
                        message = lines[j]
                        break
                diagnostics.append(
                    Diagnostic(
                        file=filename,
                        line=lineno,
                        severity="error",
                        message=Sanitizer.sanitize_text(message),
                        suggested_action=(
                            f"Fix exception in Java class {class_name} at line {lineno}."
                        ),
                        raw_excerpt=Sanitizer.sanitize_text(line),
                    )
                )
                break
    return diagnostics


def parse_csharp_dotnet_test(output: str) -> list[Diagnostic]:
    diagnostics = []
    lines = output.splitlines()
    for line in lines:
        m = re.search(r"in\s+(.*?\.cs):line\s+(\d+)", line)
        if m:
            filepath = m.group(1)
            lineno = int(m.group(2))
            diagnostics.append(
                Diagnostic(
                    file=filepath,
                    line=lineno,
                    severity="error",
                    message="dotnet test failure",
                    suggested_action=f"Fix test/logic failure at line {lineno} in {filepath}.",
                    raw_excerpt=Sanitizer.sanitize_text(line),
                )
            )
            break
    return diagnostics


def diagnose_errors(output: str, language_profile: Any | None = None) -> list[Diagnostic]:
    diagnostics = []
    diagnostics.extend(parse_python_traceback(output))
    diagnostics.extend(parse_pytest_failure(output))
    diagnostics.extend(parse_ruff_output(output))
    diagnostics.extend(parse_mypy_output(output))
    diagnostics.extend(parse_npm_tsc_output(output))
    diagnostics.extend(parse_java_stacktrace(output))
    diagnostics.extend(parse_csharp_dotnet_test(output))

    if language_profile:
        is_dict = isinstance(language_profile, dict)
        test_cmd = (
            language_profile.get("test_command")
            if is_dict
            else getattr(language_profile, "test_command", None)
        )
        if test_cmd:
            for diag in diagnostics:
                if diag.suggested_action:
                    diag.suggested_action += f" Run `{test_cmd}` to verify."
    return diagnostics
