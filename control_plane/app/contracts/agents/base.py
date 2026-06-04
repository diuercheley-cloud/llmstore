from enum import Enum
from typing import Any, Dict, Generic, Type, TypeVar

from pydantic import BaseModel, ValidationError

T_Input = TypeVar("T_Input", bound=BaseModel)
T_Output = TypeVar("T_Output", bound=BaseModel)

class CompatibilityPolicy(str, Enum):
    STRICT = "strict"  # Versions must match exactly
    BACKWARD = "backward"  # Newer code can handle older schemas
    FOWARD = "forward"  # Older code can handle newer schemas

class AgentContract(Generic[T_Input, T_Output]):
    contract_name: str
    version: str
    input_schema: Type[T_Input]
    output_schema: Type[T_Output]
    compatibility_policy: CompatibilityPolicy = CompatibilityPolicy.BACKWARD

    @classmethod
    def validate_input(cls, data: Dict[str, Any]) -> T_Input:
        try:
            return cls.input_schema.model_validate(data)
        except ValidationError as e:
            from app.contracts.base import ContractValidationError
            raise ContractValidationError(f"Input validation failed for {cls.contract_name} v{cls.version}: {e}")

    @classmethod
    def validate_output(cls, data: Dict[str, Any]) -> T_Output:
        try:
            return cls.output_schema.model_validate(data)
        except ValidationError as e:
            from app.contracts.base import ContractValidationError
            raise ContractValidationError(f"Output validation failed for {cls.contract_name} v{cls.version}: {e}")
