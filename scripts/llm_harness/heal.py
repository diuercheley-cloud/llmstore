from abc import ABC, abstractmethod


class HealRule(ABC):
    @abstractmethod
    def classify_error(self, error_text: str) -> str | None:
        """Returns a classification key if the error matches this rule."""
        pass

    @abstractmethod
    def suggest_fix(self, classification: str) -> str | None:
        """Returns a suggested fix for the given classification."""
        pass


class SQLAlchemyHealRule(HealRule):
    def classify_error(self, error_text: str) -> str | None:
        if "MissingGreenlet" in error_text or "async_orm_lazy_load" in error_text:
            return "sqlalchemy_lazy_load"
        return None

    def suggest_fix(self, classification: str) -> str | None:
        if classification == "sqlalchemy_lazy_load":
            return (
                "Use 'selectinload' or 'joinedload' in your query to avoid lazy loading "
                "in an async context. Alternatively, ensure all required attributes "
                "are loaded before closing the session."
            )
        return None


class SyntaxErrorRule(HealRule):
    def classify_error(self, error_text: str) -> str | None:
        if "SyntaxError" in error_text or "IndentationError" in error_text:
            return "syntax_error"
        if "TabError" in error_text:
            return "syntax_error"
        return None

    def suggest_fix(self, classification: str) -> str | None:
        return (
            "Check the file for syntax issues: mismatched parentheses, incorrect indentation, "
            "missing colons after def/if/for/while/class, or invalid escape sequences. "
            "Read the file, fix the syntax error, and apply the patch."
        )


class ImportErrorRule(HealRule):
    def classify_error(self, error_text: str) -> str | None:
        if "ModuleNotFoundError" in error_text or "ImportError" in error_text:
            return "import_error"
        return None

    def suggest_fix(self, classification: str) -> str | None:
        return (
            "A required module is not installed or the import path is incorrect. "
            "Check if the package needs to be installed (pip install), if the module "
            "name is correct, and if __init__.py files exist for local packages."
        )


class TestFailureRule(HealRule):
    def classify_error(self, error_text: str) -> str | None:
        if "AssertionError" in error_text or "FAILED" in error_text:
            return "test_failure"
        if "assert" in error_text.lower() and "error" in error_text.lower():
            return "test_failure"
        return None

    def suggest_fix(self, classification: str) -> str | None:
        return (
            "One or more tests failed. Read the test output carefully to identify "
            "which assertion failed and what the expected vs actual values are. "
            "Fix the source code (not the test) to make the assertion pass."
        )


class TimeoutRule(HealRule):
    def classify_error(self, error_text: str) -> str | None:
        if "TimeoutError" in error_text or "timed out" in error_text.lower():
            return "timeout_error"
        if "deadline exceeded" in error_text.lower():
            return "timeout_error"
        return None

    def suggest_fix(self, classification: str) -> str | None:
        return (
            "The operation timed out. Consider: reducing the scope of the operation, "
            "increasing the timeout, breaking the task into smaller steps, or "
            "checking for infinite loops or blocking calls in the code."
        )


class PermissionErrorRule(HealRule):
    def classify_error(self, error_text: str) -> str | None:
        if "PermissionError" in error_text or "Permission denied" in error_text:
            return "permission_error"
        if "EACCES" in error_text:
            return "permission_error"
        return None

    def suggest_fix(self, classification: str) -> str | None:
        return (
            "The operation was denied due to insufficient permissions. Check file "
            "ownership and permissions, ensure the workspace path is writable, "
            "and avoid accessing system directories or protected files."
        )


class DependencyErrorRule(HealRule):
    def classify_error(self, error_text: str) -> str | None:
        if "pkg_resources" in error_text or "DistributionNotFound" in error_text:
            return "dependency_error"
        if "version conflict" in error_text.lower():
            return "dependency_error"
        if "No matching distribution" in error_text:
            return "dependency_error"
        return None

    def suggest_fix(self, classification: str) -> str | None:
        return (
            "There is a dependency version conflict or missing package. Check "
            "requirements.txt or pyproject.toml for version constraints, update "
            "the dependency specification, and ensure compatible versions are used."
        )


class HealEngine:
    """Analyzes errors and suggests fixes using a rule-based approach.

    Supports error frequency tracking to detect repeated failures.
    """

    def __init__(self, rules: list[HealRule] | None = None, max_repeated: int = 3):
        self.rules = rules or [
            SyntaxErrorRule(),
            ImportErrorRule(),
            TestFailureRule(),
            TimeoutRule(),
            PermissionErrorRule(),
            DependencyErrorRule(),
            SQLAlchemyHealRule(),
        ]
        self.max_repeated = max_repeated
        self._error_counts: dict[str, int] = {}

    def analyze_error(self, error_text: str) -> dict[str, str]:
        for rule in self.rules:
            classification = rule.classify_error(error_text)
            if classification:
                # Track frequency
                self._error_counts[classification] = self._error_counts.get(classification, 0) + 1
                count = self._error_counts[classification]

                suggestion = rule.suggest_fix(classification)
                result = {
                    "classification": classification,
                    "suggestion": suggestion or "No suggestion available",
                    "occurrence": str(count),
                }

                if count >= self.max_repeated:
                    result["escalation"] = (
                        f"Error '{classification}' has occurred {count} times. "
                        "Consider aborting or trying a fundamentally different approach."
                    )
                return result

        self._error_counts["unknown"] = self._error_counts.get("unknown", 0) + 1
        return {
            "classification": "unknown",
            "suggestion": "No automated fix available",
            "occurrence": str(self._error_counts["unknown"]),
        }

    def reset_counts(self) -> None:
        """Reset error frequency counters. Call at the start of each run."""
        self._error_counts.clear()

    def is_escalated(self, classification: str) -> bool:
        """Check if an error classification has exceeded the repeat threshold."""
        return self._error_counts.get(classification, 0) >= self.max_repeated
