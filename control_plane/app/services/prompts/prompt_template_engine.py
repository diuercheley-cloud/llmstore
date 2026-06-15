# Owner: agent-platform
from typing import Any

import jsonschema
from jinja2 import Environment, meta


class PromptTemplateEngine:
    """
    Handles rendering of prompt templates and variable validation.
    Uses Jinja2 for rendering and JSON Schema for validation.
    """

    def __init__(self):
        self.env = Environment()

    def render(
        self, template_str: str, variables: dict[str, Any], schema: dict[str, Any] = None
    ) -> str:
        """
        Renders a template string with given variables.
        Optional schema validation for variables.
        """
        if schema:
            jsonschema.validate(instance=variables, schema=schema)

        template = self.env.from_string(template_str)
        return template.render(**variables)

    def extract_variables(self, template_str: str) -> set[str]:
        """
        Extracts all variable names from a Jinja2 template string.
        """
        ast = self.env.parse(template_str)
        return meta.find_undeclared_variables(ast)

    def validate_variables(self, template_str: str, variables: dict[str, Any]):
        """
        Ensures all variables required by the template are provided.
        """
        required = self.extract_variables(template_str)
        provided = set(variables.keys())
        missing = required - provided
        if missing:
            raise ValueError(f"Missing required variables: {missing}")
