import json
import os
import time
from typing import Any

from ..sanitizer import Sanitizer
from .schema import EvalResult


class EvalReportGenerator:
    @staticmethod
    def generate_summary(result: EvalResult) -> dict[str, Any]:
        case_results = []
        judge_scores = []
        for cs in result.case_scores:
            entry: dict[str, Any] = {
                "case_id": cs.case_id,
                "passed": cs.passed,
                "checks": cs.checks,
                "details": Sanitizer.sanitize_data(cs.details),
                "duration_seconds": round(cs.duration_seconds, 2),
                "error": Sanitizer.sanitize_text(cs.error) if cs.error else None,
            }
            if cs.judge_verdict:
                entry["judge_verdict"] = Sanitizer.sanitize_data(cs.judge_verdict.model_dump())
                judge_scores.append(cs.judge_verdict.score)
            case_results.append(entry)

        summary: dict[str, Any] = {
            "suite_name": result.suite_name,
            "total_cases": result.total_cases,
            "passed": result.passed,
            "failed": result.failed,
            "accuracy": round(result.accuracy, 4),
            "pass_at_1": round(result.pass_at_1, 4),
            "total_duration_seconds": round(result.total_duration_seconds, 2),
            "case_results": Sanitizer.sanitize_data(case_results),
            "total_tokens": result.total_tokens,
        }
        if judge_scores:
            summary["judge_avg_score"] = round(sum(judge_scores) / len(judge_scores), 4)
        return summary

    @staticmethod
    def save_json_report(result: EvalResult, output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = int(time.time())
        filename = f"eval_report_{timestamp}.json"
        summary = EvalReportGenerator.generate_summary(result)
        summary = Sanitizer.sanitize_data(summary)

        path = os.path.join(output_dir, filename)
        with open(path, "w") as f:
            json.dump(summary, f, indent=2)
        return path

    @staticmethod
    def generate_markdown_report(result: EvalResult) -> str:
        passed_str = f"{result.passed}/{result.total_cases}"
        accuracy_pct = f"{result.accuracy * 100:.1f}%"
        duration_str = f"{result.total_duration_seconds:.2f}s"

        judge_scores = [
            cs.judge_verdict.score for cs in result.case_scores if cs.judge_verdict is not None
        ]
        judge_avg = sum(judge_scores) / len(judge_scores) if judge_scores else None

        lines = [
            f"# Eval Report: {result.suite_name}",
            "",
            f"**Total Cases**: {result.total_cases}  ",
            f"**Passed**: {result.passed}  ",
            f"**Failed**: {result.failed}  ",
            f"**Accuracy**: {accuracy_pct}  ",
            f"**pass@1**: {result.pass_at_1:.4f}  ",
            f"**Total Duration**: {duration_str}  ",
        ]
        if judge_avg is not None:
            lines.append(f"**Judge Avg Score**: {judge_avg:.4f}  ")
        if result.total_tokens:
            lines.append(f"**Total Tokens**: {result.total_tokens}  ")
        lines.append("")

        lines.append("## Per-Case Results")
        lines.append("")
        headers = "| Case ID | Status | Checks | Duration | Error |"
        if judge_scores:
            headers = "| Case ID | Status | Checks | Judge | Duration | Error |"
        lines.append(headers)
        sep = "| :--- | :--- | :--- | :--- | :--- |"
        if judge_scores:
            sep = "| :--- | :--- | :--- | :--- | :--- | :--- |"
        lines.append(sep)

        for cs in result.case_scores:
            status = "✅ PASS" if cs.passed else "❌ FAIL"
            checks_str = ", ".join(f"{k}={'✓' if v else '✗'}" for k, v in cs.checks.items())
            dur = f"{cs.duration_seconds:.2f}s"
            err = Sanitizer.sanitize_text(cs.error or "")[:80] if cs.error else ""
            if cs.judge_verdict:
                jscore = f"{cs.judge_verdict.score:.2f}"
                lines.append(
                    f"| {cs.case_id} | {status} | {checks_str} | {jscore} | {dur} | {err} |"
                )
            else:
                lines.append(f"| {cs.case_id} | {status} | {checks_str} | {dur} | {err} |")

        lines.extend(
            [
                "",
                "## Summary",
                "",
                f"- **Suite**: {result.suite_name}",
                f"- **Passed**: {passed_str}",
                f"- **Accuracy**: {accuracy_pct}",
                f"- **pass@1**: {result.pass_at_1:.4f}",
                f"- **Total Duration**: {duration_str}",
            ]
        )
        if judge_avg is not None:
            lines.append(f"- **Judge Avg Score**: {judge_avg:.4f}")
        if result.total_tokens:
            lines.append(f"- **Total Tokens**: {result.total_tokens}")
        lines.append("")

        failed_cases = [cs for cs in result.case_scores if not cs.passed]
        if failed_cases:
            lines.append("## Failed Cases Detail")
            lines.append("")
            for cs in failed_cases:
                lines.append(f"### {cs.case_id}")
                lines.append("")
                lines.append(f"- **Error**: {Sanitizer.sanitize_text(cs.error or 'N/A')}")
                lines.append(f"- **Duration**: {cs.duration_seconds:.2f}s")
                failed_checks = [k for k, v in cs.checks.items() if not v]
                if failed_checks:
                    lines.append("- **Failed Checks**:")
                    for fc in failed_checks:
                        lines.append(f"  - {fc}")
                if cs.judge_verdict:
                    jv = cs.judge_verdict
                    lines.append(f"- **Judge Score**: {jv.score:.2f}")
                    lines.append(f"- **Judge Risk**: {jv.risk_level}")
                    if jv.reason:
                        lines.append(f"- **Judge Reason**: {Sanitizer.sanitize_text(jv.reason)}")
                    if jv.weaknesses:
                        lines.append("- **Weaknesses**:")
                        for w in jv.weaknesses:
                            lines.append(f"  - {Sanitizer.sanitize_text(w)}")
                lines.append("")

        return "\n".join(lines)

    @staticmethod
    def save_markdown_report(result: EvalResult, output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = int(time.time())
        filename = f"eval_report_{timestamp}.md"
        md_content = EvalReportGenerator.generate_markdown_report(result)

        path = os.path.join(output_dir, filename)
        with open(path, "w") as f:
            f.write(md_content)
        return path
