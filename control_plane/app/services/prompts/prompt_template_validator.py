# Owner: agent-platform
import logging
import re
from typing import Any

from app.services.prompts.prompt_template_renderer import PromptTemplateRenderer

logger = logging.getLogger(__name__)

SECRET_IN_CONTENT_PATTERNS = [
    re.compile(r"api_key['\"]?\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}", re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"password['\"]?\s*[:=]\s*['\"][a-zA-Z0-9_\-]+", re.IGNORECASE),
    re.compile(r"secret['\"]?\s*[:=]\s*['\"][a-zA-Z0-9_\-]+", re.IGNORECASE),
    re.compile(r"token['\"]?\s*[:=]\s*['\"][a-zA-Z0-9_\-\.]+", re.IGNORECASE),
]

UNSAFE_INSTRUCTION_PATTERNS = [
    r"ignore (all )?(previous|system|above) (instructions|prompts|commands)",
    r"output your (system |)(message|prompt|instructions)",
    r"bypass (all )?(filters|restrictions|safety)",
    r"you are now (an? )?(ai|assistant) without (any )?(restrictions|rules|limits)",
    r"print your (system )?prompt",
    r"repeat (everything |)(above|the prompt)",
]


class TemplateValidationResult:
    def __init__(
        self,
        valid: bool,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ):
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class PromptTemplateValidator:
    def __init__(self):
        self.renderer = PromptTemplateRenderer()

    def validate_template_content(self, content: str) -> TemplateValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        try:
            self.renderer.validate_template_syntax(content)
        except ValueError as e:
            errors.append(str(e))
            return TemplateValidationResult(valid=False, errors=errors)

        used_vars = self.renderer.extract_variables(content)

        for pattern in SECRET_IN_CONTENT_PATTERNS:
            if pattern.search(content):
                warnings.append("Content may contain hardcoded secrets or API keys")

        for pattern in UNSAFE_INSTRUCTION_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append(f"Potentially unsafe instruction detected: {pattern}")

        if len(content) > 32000:
            warnings.append("Template content exceeds 32000 characters")

        return TemplateValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_variable_declaration(
        self, var_name: str, var_type: str
    ) -> TemplateValidationResult:
        errors: list[str] = []

        if not var_name or not var_name.strip():
            errors.append("Variable name cannot be empty")

        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", var_name):
            errors.append(f"Variable name '{var_name}' must be a valid Python identifier")

        valid_types = {"string", "number", "boolean", "object", "array", "any"}
        if var_type not in valid_types:
            errors.append(f"Invalid variable type '{var_type}'. Must be one of: {valid_types}")

        return TemplateValidationResult(valid=len(errors) == 0, errors=errors)

    def validate_variables_satisfy_template(
        self, content: str, declared_vars: list[dict[str, Any]] | None = None
    ) -> TemplateValidationResult:
        errors: list[str] = []

        try:
            used_vars = self.renderer.extract_variables(content)
        except ValueError as e:
            errors.append(str(e))
            return TemplateValidationResult(valid=False, errors=errors)

        if declared_vars:
            declared_names = {v["name"] for v in declared_vars}
            undeclared = used_vars - declared_names
            if undeclared:
                errors.append(f"Template uses variables not declared: {undeclared}")

        return TemplateValidationResult(valid=len(errors) == 0, errors=errors)

    def validate_version_promotion(
        self, version: Any, target_status: str
    ) -> TemplateValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        content_validation = self.validate_template_content(version.content)
        errors.extend(content_validation.errors)
        warnings.extend(content_validation.warnings)

        if target_status == "production" and version.status not in ("staging", "production"):
            errors.append(
                f"Cannot promote to production from '{version.status}'. Must promote to staging first."
            )

        return TemplateValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
