# Owner: agent-platform
from typing import Any

from .constraint_model import Constraint, ConstraintModel


class ConstraintValidator:
    """
    Simple rule-based validator used as a fallback when formal solvers are unavailable.
    """

    def validate(self, model: ConstraintModel, plan_data: dict[str, Any]) -> list[dict[str, str]]:
        errors = []
        for c in model.constraints:
            field_value = plan_data.get(c.target_field)
            if field_value is None:
                continue

            if not self._check_constraint(c, field_value):
                errors.append(
                    {
                        "id": c.id,
                        "message": c.message
                        or f"Constraint {c.id} violated on field {c.target_field}",
                    }
                )
        return errors

    def _check_constraint(self, c: Constraint, value: Any) -> bool:
        try:
            if c.operator == "eq":
                return value == c.value
            if c.operator == "gt":
                return value > c.value
            if c.operator == "lt":
                return value < c.value
            if c.operator == "ge":
                return value >= c.value
            if c.operator == "le":
                return value <= c.value
            if c.operator == "neq":
                return value != c.value
            if c.operator == "in":
                return value in c.value
        except (TypeError, ValueError):
            return False
        return True
