from .schema import CaseScore, EvalCase, EvalResult, EvalSuite


def score_case(
    case: EvalCase,
    harness_result,
    case_duration: float,
    test_command_result: dict | None = None,
) -> CaseScore:
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}
    error: str | None = None

    # 1. Harness execution success
    harness_ok = harness_result.success
    checks["harness_success"] = harness_ok
    details["harness_error"] = harness_result.error

    # 2. Test command (if configured)
    if case.test_command:
        test_ok = _check_test_command(harness_result, case.test_command, test_command_result)
        checks["test_command"] = test_ok

    # 3. Expected stdout (if configured)
    if case.expected_stdout is not None:
        stdout_ok = _check_expected_stdout(harness_result, case.expected_stdout)
        checks["expected_stdout"] = stdout_ok

    # 4. Expected status (if configured)
    if case.expected_status is not None:
        status_ok = _check_expected_status(harness_result, case.expected_status)
        checks["expected_status"] = status_ok

    # 5. Expected files (if configured)
    if case.expected_files:
        file_checks = _check_expected_files(harness_result, case.expected_files)
        checks.update(file_checks)
        details["file_checks"] = {k: bool(v) for k, v in file_checks.items()}

    # Run plugin custom scorers
    from ..plugins import plugin_registry

    for name, scorer_fn in plugin_registry.list_scorers().items():
        try:
            score_ok = scorer_fn(case, harness_result)
            checks[f"plugin_scorer:{name}"] = bool(score_ok)
        except Exception as e:
            checks[f"plugin_scorer:{name}"] = False
            if not error:
                error = f"Plugin scorer {name} failed: {e}"

    passed = all(checks.values()) if checks else harness_ok
    if not passed and not error:
        failed_checks = [k for k, v in checks.items() if not v]
        error = f"Failed checks: {', '.join(failed_checks)}"

    return CaseScore(
        case_id=case.id,
        passed=passed,
        checks=checks,
        details=details,
        duration_seconds=case_duration,
        error=error,
    )


def _check_test_command(
    harness_result,
    test_command: str,
    test_command_result: dict | None = None,
) -> bool:
    if test_command_result is not None:
        return test_command_result.get("returncode", -1) == 0
    events = getattr(harness_result, "events", []) or []
    for ev in events:
        if ev.get("action_type") == "run_shell" and ev.get("event") == "action.completed":
            cmd = (ev.get("metadata") or {}).get("command", "")
            if test_command in cmd:
                return True
        if ev.get("action_type") == "run_tests" and ev.get("event") == "action.completed":
            return True
    return False


def _check_expected_stdout(harness_result, expected: str) -> bool:
    output = harness_result.output or ""
    events = getattr(harness_result, "events", []) or []
    for ev in events:
        msg = ev.get("message", "") or ""
        output += msg
    return expected in output


def _check_expected_status(harness_result, expected: int) -> bool:
    events = getattr(harness_result, "events", []) or []
    for ev in events:
        metadata = ev.get("metadata") or {}
        retcode = metadata.get("returncode")
        if retcode is not None and int(retcode) == expected:
            return True
    return expected == 0 and harness_result.success


def _check_expected_files(harness_result, expected_files: dict[str, str]) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    events = getattr(harness_result, "events", []) or []
    patch_files: set[str] = set()
    for ev in events:
        metadata = ev.get("metadata") or {}
        changed = metadata.get("changed_files", []) or []
        patch_files.update(changed)

    for filepath, _expected_content in expected_files.items():
        checks[f"file_match:{filepath}"] = filepath in patch_files
    return checks


class Scorer:
    @staticmethod
    def aggregate(suite: EvalSuite, case_scores: list[CaseScore]) -> EvalResult:
        total = len(case_scores)
        passed = sum(1 for s in case_scores if s.passed)
        failed = total - passed
        total_duration = sum(s.duration_seconds for s in case_scores)

        accuracy = passed / total if total > 0 else 0.0
        pass_at_1 = accuracy

        return EvalResult(
            suite_name=suite.name,
            total_cases=total,
            passed=passed,
            failed=failed,
            accuracy=accuracy,
            pass_at_1=pass_at_1,
            total_duration_seconds=total_duration,
            case_scores=case_scores,
        )

    @staticmethod
    def generate_feedback(result: EvalResult) -> str:
        if result.passed == result.total_cases:
            return "All evaluation cases passed. Strategy is optimal."

        failed_cases = [s for s in result.case_scores if not s.passed]

        feedback = f"Evaluation feedback: {result.passed}/{result.total_cases} cases passed.\n"
        feedback += "Common failure points identified:\n"

        failure_reasons: dict[str, int] = {}
        for s in failed_cases:
            reason = s.error or "Unknown failure"
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

        for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)[:3]:
            feedback += f"- {reason} ({count} occurrences)\n"

        return feedback
