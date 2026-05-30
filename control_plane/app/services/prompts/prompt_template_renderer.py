# Owner: agent-platform
import re
import hashlib
import json
import logging
from typing import Any, Dict, Optional, Set, Tuple

from jinja2 import Environment, Template, meta, TemplateError, UndefinedError
from jinja2.sandbox import SandboxedEnvironment

logger = logging.getLogger(__name__)

SECRET_VALUE_PATTERNS = [
    re.compile(r"^(sk-|pk-|whsec_|wh_|xox[bpors]-)[a-zA-Z0-9]{10,}", re.IGNORECASE),
    re.compile(r"^[a-zA-Z0-9_\-\.]{32,}$"),
]

BLOCKED_VARIABLE_NAMES = {
    "eval", "exec", "__import__", "open", "system", "globals", "locals",
    "compile", "__builtins__", "__class__", "__bases__", "__subclasses__",
}


class VariableIsSecretError(ValueError):
    pass


class UnsafeVariableNameError(ValueError):
    pass


class TemplateSyntaxError(ValueError):
    pass


class PromptTemplateRenderer:
    def __init__(self):
        self.env = SandboxedEnvironment(
            autoescape=False,
            undefined=self._strict_undefined,
        )

    @staticmethod
    def _strict_undefined():
        raise UndefinedError("Undefined variable")

    def _check_variable_name_is_safe(self, name: str) -> None:
        if name in BLOCKED_VARIABLE_NAMES:
            raise UnsafeVariableNameError(
                f"Variable name '{name}' is blocked for security reasons"
            )

    def _check_value_is_not_secret(self, name: str, value: Any) -> None:
        if not isinstance(value, str):
            return
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.match(value.strip()):
                raise VariableIsSecretError(
                    f"Variable '{name}' contains a value that looks like a secret/token. "
                    f"Use a secret store instead of inline variables."
                )

    def _check_value_not_unsafe(self, name: str, value: Any) -> None:
        if isinstance(value, (dict, list, tuple)):
            raise UnsafeVariableNameError(
                f"Variable '{name}' must be a primitive type (str, int, float, bool), not {type(value).__name__}"
            )

    def extract_variables(self, template_str: str) -> Set[str]:
        ast = self.env.parse(template_str)
        return meta.find_undeclared_variables(ast)

    def validate_template_syntax(self, template_str: str) -> None:
        try:
            self.env.parse(template_str)
        except TemplateError as e:
            raise TemplateSyntaxError(f"Template syntax error: {e}")

    def validate_variables_against_declaration(
        self,
        template_str: str,
        variables: Dict[str, Any],
        declared_vars: Optional[list] = None,
    ) -> None:
        self.validate_template_syntax(template_str)
        used_vars = self.extract_variables(template_str)

        if declared_vars:
            declared_names = {v["name"] for v in declared_vars}
            undeclared = used_vars - declared_names
            if undeclared:
                raise ValueError(
                    f"Variables used in template but not declared: {undeclared}"
                )

            for decl in declared_vars:
                name = decl["name"]
                if decl.get("required", True) and name not in variables and decl.get("default") is None:
                    raise ValueError(f"Required variable '{name}' is missing")
                if name in variables:
                    self._check_variable_name_is_safe(name)
                    self._check_value_is_not_secret(name, variables[name])

    def render(
        self,
        template_str: str,
        variables: Dict[str, Any],
        declared_vars: Optional[list] = None,
        skip_secret_check: bool = False,
    ) -> Tuple[str, str, str]:
        declared_names = {v["name"] for v in declared_vars} if declared_vars else set()

        for name in variables:
            self._check_variable_name_is_safe(name)

            if not skip_secret_check:
                self._check_value_is_not_secret(name, variables[name])

        for name in declared_names:
            if name in variables:
                self._check_variable_name_is_safe(name)

        sanitized_vars = {}
        for name, value in variables.items():
            if isinstance(value, str):
                value = value.strip()
            sanitized_vars[name] = value

        if declared_vars:
            for decl in declared_vars:
                name = decl["name"]
                if name not in sanitized_vars and decl.get("default") is not None:
                    sanitized_vars[name] = decl["default"]

        try:
            template = self.env.from_string(template_str)
            rendered = template.render(**sanitized_vars)
        except UndefinedError as e:
            raise ValueError(f"Missing variable in template: {e}")
        except TemplateError as e:
            raise ValueError(f"Template rendering error: {e}")

        variables_json = json.dumps(sanitized_vars, sort_keys=True)
        variables_hash = hashlib.sha256(variables_json.encode("utf-8")).hexdigest()
        output_hash = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        rendered_content_hash = hashlib.sha256(
            json.dumps({"template": template_str, "variables": sanitized_vars}, sort_keys=True).encode("utf-8")
        ).hexdigest()

        return rendered, variables_hash, output_hash, rendered_content_hash

    def resolve_instructions(
        self,
        template_str: Optional[str],
        instructions: Optional[str],
        variables: Optional[Dict[str, Any]] = None,
        declared_vars: Optional[list] = None,
    ) -> Tuple[str, Optional[Dict[str, str]]]:
        if template_str:
            rendered, vhash, ohash, chash = self.render(
                template_str, variables or {}, declared_vars=declared_vars
            )
            hashes = {
                "variables_hash": vhash,
                "output_hash": ohash,
                "rendered_content_hash": chash,
            }
            return rendered, hashes
        return instructions or "", None
