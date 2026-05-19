from typing import Protocol, runtime_checkable, Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ContractError(Exception):
    """Base class for all contract-related errors."""
    pass

class ContractValidationError(ContractError):
    """Raised when data does not conform to the contract."""
    pass

class ContractExecutionError(ContractError):
    """Raised when a contract method fails during execution."""
    pass

@runtime_checkable
class BaseContract(Protocol):
    """Base protocol for all platform contracts."""
    
    def validate_contract(self) -> bool:
        """
        Validates the implementation against the contract definitions.
        Should perform runtime checks if possible.
        """
        ...

class ContractCapability(BaseModel):
    """Base class for capability flags."""
    pass
