# ConfigService - Centralized Configuration Management

The `ConfigService` provides a unified interface for managing and inspecting the platform's configuration, consolidating various sources into a single "effective configuration".

## Precedence Layers

When a configuration key is requested, the `ConfigService` resolves it using the following precedence (from highest to lowest):

1. **Runtime Overrides**: Values set explicitly during application execution (non-persistent).
2. **Environment Variables**: Variables set in the OS environment or via `.env` files.
3. **Configuration Files**: YAML or JSON files located in the `config/` directory.
4. **Code Defaults**: Default values defined in Pydantic `Settings` classes.

## Configuration Sources

The service automatically loads and indexes configurations from:
- `config/*.yaml` and `config/*.json`
- `config/feature-flags.yaml` (indexed by flag name)
- Pydantic `Settings` (consolidating `.env` and defaults)

## Usage in Python

### Basic Access
```python
from app.services.config_service import get_config_service

config = get_config_service()
is_enabled = config.get("FEATURE_X_ENABLED")
```

### Detailed Inspection
```python
detailed = config.get_detailed("FEATURE_X_ENABLED")
print(f"Value: {detailed.value}")
print(f"Source: {detailed.source}")
print(f"Default: {detailed.default_value}")
print(f"Is Overridden: {detailed.is_overridden}")
```

### Runtime Overrides
```python
config.set_runtime_override("MAINTENANCE_MODE", True)
```

## Admin API

The service provides endpoints for inspecting the effective configuration:

- `GET /admin/config/effective`: Returns a list of all configuration keys with their effective values and metadata. Secrets are redacted by default.
- `GET /admin/config/detailed/{key}`: Returns detailed information for a specific key.

## Secret Redaction

The `ConfigService` automatically redacts sensitive information based on key patterns. Keys containing the following terms are redacted in API responses:
`KEY`, `PASSWORD`, `SECRET`, `TOKEN`, `AUTH`, `PWD`, `CERT`, `PRIVATE`.

## Implementation Details

- **Singleton**: The service is implemented as a singleton to ensure consistency across the application.
- **Lazy Loading**: Configurations are loaded once during initialization.
- **Case Insensitivity**: Key lookups are normalized to uppercase, while internal Pydantic field mapping handles lowercase conversion.
