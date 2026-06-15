import re
from dataclasses import asdict, dataclass, field


@dataclass
class ParsedFailure:
    location: str = ""
    message: str = ""
    severity: str = "error"


@dataclass
class ParsedOutput:
    kind: str = "generic"
    summary: str = ""
    failures: list[ParsedFailure] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def parse_output(command: str, output: str, returncode: int) -> ParsedOutput:
    normalized = command.lower()
    if "pytest" in normalized:
        return parse_pytest_output(output, returncode)
    if "ruff" in normalized:
        return parse_ruff_output(output, returncode)
    if "mypy" in normalized:
        return parse_mypy_output(output, returncode)
    return parse_generic_failure(output, returncode)


def parse_pytest_output(output: str, returncode: int) -> ParsedOutput:
    failures: list[ParsedFailure] = []
    for line in output.splitlines():
        match = re.match(r"^(?P<location>[\w./\\-]+::[\w\[\].-]+)\s+-\s+(?P<message>.+)$", line)
        if match:
            failures.append(
                ParsedFailure(location=match.group("location"), message=match.group("message"))
            )
            continue
        match = re.match(
            r"^FAILED\s+(?P<location>[\w./\\-]+::[\w\[\].-]+)\s+-\s+(?P<message>.+)$",
            line,
        )
        if match:
            failures.append(
                ParsedFailure(location=match.group("location"), message=match.group("message"))
            )
    error_count = len(failures)
    summary = (
        "pytest passed" if returncode == 0 else f"pytest reported {error_count or 1} failure(s)"
    )
    return ParsedOutput(
        kind="pytest",
        summary=summary,
        failures=failures,
        error_count=error_count if returncode != 0 else 0,
    )


def parse_ruff_output(output: str, returncode: int) -> ParsedOutput:
    failures: list[ParsedFailure] = []
    for line in output.splitlines():
        match = re.match(r"^(?P<location>[^:]+:\d+:\d+):\s+(?P<message>.+)$", line)
        if match:
            failures.append(
                ParsedFailure(location=match.group("location"), message=match.group("message"))
            )
    error_count = len(failures)
    summary = "ruff passed" if returncode == 0 else f"ruff reported {error_count or 1} issue(s)"
    return ParsedOutput(
        kind="ruff",
        summary=summary,
        failures=failures,
        error_count=error_count if returncode != 0 else 0,
    )


def parse_mypy_output(output: str, returncode: int) -> ParsedOutput:
    failures: list[ParsedFailure] = []
    warning_count = 0
    for line in output.splitlines():
        match = re.match(
            r"^(?P<location>[^:]+:\d+):\s+(?P<severity>error|note|warning):\s+(?P<message>.+)$",
            line,
        )
        if not match:
            continue
        severity = match.group("severity")
        if severity in {"note", "warning"}:
            warning_count += 1
        else:
            failures.append(
                ParsedFailure(
                    location=match.group("location"),
                    message=match.group("message"),
                    severity=severity,
                )
            )
    error_count = len(failures)
    summary = "mypy passed" if returncode == 0 else f"mypy reported {error_count or 1} error(s)"
    return ParsedOutput(
        kind="mypy",
        summary=summary,
        failures=failures,
        error_count=error_count if returncode != 0 else 0,
        warning_count=warning_count,
    )


def parse_generic_failure(output: str, returncode: int) -> ParsedOutput:
    failures: list[ParsedFailure] = []
    for line in output.splitlines():
        if re.search(r"\b(error|failed|exception)\b", line, re.IGNORECASE):
            failures.append(ParsedFailure(message=line.strip()))
    summary = (
        "command passed"
        if returncode == 0
        else (f"command failed with {len(failures) or 1} detected error line(s)")
    )
    return ParsedOutput(
        kind="generic",
        summary=summary,
        failures=failures[:20],
        error_count=(len(failures) if failures else int(returncode != 0)),
        warning_count=len(
            [line for line in output.splitlines() if re.search(r"\bwarning\b", line, re.IGNORECASE)]
        ),
    )
