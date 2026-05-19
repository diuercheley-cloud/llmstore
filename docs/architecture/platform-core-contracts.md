# Platform Core Contracts

This document describes the explicit and testable contracts implemented in the `llm-inference-stack` to prevent architectural drift between core components.

## Overview

Platform Core Contracts define mandatory interfaces and data structures for critical platform services. They use Python `Protocol` for interface definition and `Pydantic` for data validation.

## List of Contracts

### 1. ProviderContract
Defines the interface for LLM providers (OpenAI, Anthropic, Local, etc.).
- **Key Methods**: `chat_completion`, `embeddings`, `health_check`, `list_models`.
- **Location**: `app/contracts/provider.py`

### 2. PluginContract
Defines the interface for the platform's plugin system.
- **Key Methods**: `load_plugin`, `validate_manifest`.
- **Location**: `app/contracts/plugin.py`

### 3. RoutingContract
Defines the interface for smart routers.
- **Key Methods**: `route`, `get_policy`.
- **Location**: `app/contracts/routing.py`

### 4. TokenAccountingContract
Defines the interface for token counting and accounting services.
- **Key Methods**: `count_text_tokens`, `count_chat_tokens`.
- **Location**: `app/contracts/token_accounting.py`

### 5. AttestationContract
Defines the interface for node and system attestation.
- **Key Methods**: `generate_report`, `verify_report`.
- **Location**: `app/contracts/attestation.py`

### 6. QueueContract
Defines the interface for request queuing and concurrency control.
- **Key Methods**: `slot`, `get_snapshot`.
- **Location**: `app/contracts/queue.py`

### 7. EventContract
Defines the interface for platform-wide event logging.
- **Key Methods**: `log_event`, `list_events`.
- **Location**: `app/contracts/event.py`

### 8. ModelRuntimeContract
Defines the interface for model runtime management (hot-swap, loading/unloading).
- **Key Methods**: `load_model`, `unload_model`, `activate_model`, `get_model_health`.
- **Location**: `app/contracts/model_runtime.py`

## Implementation Rules

1. **Explicit Implementation**: Core services must explicitly inherit from their respective contracts.
2. **Type Safety**: Use Pydantic models defined in contracts for inputs and outputs. Avoid using generic `dict` where a model exists.
3. **Capability Flags**: Each contract provides a `capabilities()` method to signal supported features.
4. **Contract Validation**: All contracts must implement `validate_contract()` for runtime verification.

## Testing

Contract implementations are verified in `tests/contracts/`. Any new implementation of a contract must pass these tests.
