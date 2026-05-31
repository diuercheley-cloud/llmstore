# Prompt Template Engine

## Overview

The Prompt Template Engine replaces raw system instructions in agents with versioned, parametrizable, and auditable templates. This ensures consistency across different agents and allows for safe testing of prompt changes.

## Features

- **Jinja2 Syntax**: Use standard `{{ variable }}` syntax for parametrizing prompts.
- **Sandboxed Execution**: Templates are rendered in a restricted environment to prevent unauthorized code execution.
- **Immutable Versioning**: Each change creates a new version. Versions can be promoted from `draft` to `staging` and `production`.
- **Variable Validation**: Templates must declare the variables they use, ensuring all required data is provided during rendering.
- **Rendering Audit**: Every template render is recorded with hashes of inputs and outputs for debugging and compliance.
- **Secret Protection**: The engine automatically detects and blocks rendering if variables appear to contain sensitive tokens (API keys, secrets).

## Data Models

### Prompt Templates
- `id` — unique identifier
- `tenant_id` — multi-tenant isolation
- `name` — human-readable name
- `active_version_id` — the currently live version for this template

### Template Versions
- `template_id` — reference to the parent template
- `version_tag` — semantic version or timestamp
- `content` — the Jinja2 template string
- `status` — `draft`, `staging`, `production`, `archived`

### Template Variables
- `name` — variable name (must be a valid identifier)
- `var_type` — `string`, `number`, `boolean`, `object`, `array`
- `required` — whether rendering fails if this variable is missing
- `default` — optional fallback value

## API Reference

### Create Template
```
POST /admin/prompts/templates
```

### Declare Variable
```
POST /admin/prompts/templates/{id}/variables
```

### Create Version
```
POST /admin/prompts/templates/{id}/versions
```

### Render Template (Preview)
```
POST /admin/prompts/templates/{id}/render
```

### Promote Version
```
POST /admin/prompts/templates/{id}/versions/{version_id}/promote
```

## Security Sandbox

The template engine uses a `SandboxedEnvironment` from Jinja2, which blocks access to unsafe Python attributes (e.g., `__subclasses__`, `__init__`). Additionally, the LLM Stack engine:
- Blocks variables named after dangerous functions (`eval`, `exec`, `__import__`).
- Redacts PII and secrets from variables before injection.
- Limits template content size to 32KB.
