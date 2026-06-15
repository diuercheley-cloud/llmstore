import json
import os

import yaml
from pydantic import ValidationError

from .schema import EvalSuite


class EvalLoadError(Exception):
    pass


class EvalSchemaError(EvalLoadError):
    pass


class EvalLoader:
    @staticmethod
    def load(path: str) -> EvalSuite:
        if not os.path.exists(path):
            raise EvalLoadError(f"eval_suite file not found: {path}")

        try:
            with open(path) as f:
                data = yaml.safe_load(f) if path.endswith((".yaml", ".yml")) else json.load(f)
        except json.JSONDecodeError as e:
            raise EvalLoadError(f"Failed to parse eval_suite JSON: {e}") from e
        except yaml.YAMLError as e:
            raise EvalLoadError(f"Failed to parse eval_suite YAML: {e}") from e
        except Exception as e:
            raise EvalLoadError(f"Failed to load eval_suite from {path}: {e}") from e

        if not isinstance(data, dict):
            raise EvalSchemaError("eval_suite must be a mapping (JSON object or YAML dict)")

        # Normalization for backward compatibility
        if "test_cases" in data and "cases" not in data:
            data["cases"] = data.pop("test_cases")

        for i, case in enumerate(data.get("cases", [])):
            if not isinstance(case, dict):
                continue
            # Normalize case task
            if "input" in case and "task" not in case:
                case["task"] = case.pop("input")
            elif "input_text" in case and "task" not in case:
                case["task"] = case.pop("input_text")

            # Normalize case id
            if "name" in case and "id" not in case:
                case["id"] = case.pop("name")
            if "id" not in case:
                case["id"] = str(i)

            # Apply defaults
            if "timeout_seconds" not in case:
                case["timeout_seconds"] = 300
            if "tags" not in case:
                case["tags"] = []
            if "expected_status" not in case:
                case["expected_status"] = 0

        try:
            return EvalSuite.model_validate(data)
        except ValidationError as e:
            raise EvalSchemaError(f"Invalid eval_suite schema: {e}") from e
