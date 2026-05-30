# Prompt Management System

The Prompt Management system turns prompts into governed, versioned, and testable assets.

## Core Components

### 1. Template Library
Prompts are defined as templates with variables using Jinja2 syntax (e.g., `Hello {{name}}`).

### 2. Versioning and Immutability
- Every change creates a new version.
- Versions are immutable once created.
- Lifecycle stages: `draft` -> `staging` -> `production`.
- **Rollback**: Quickly revert the active version of a template to a previous known-good state.

### 3. Template Engine
- **Rendering**: Templates are rendered with variables.
- **Schema Validation**: Define JSON schemas for variables to ensure input data is correct.
- **Auto-extraction**: Automatically identify required variables from template strings.

### 4. Prompt Playground
- Test prompts interactively with different variables.
- Execute against mock or real LLM providers.
- Track latency and token usage for each run.

### 5. A/B Testing
- Orchestrate experiments between two prompt versions.
- Control traffic split (e.g., 50/50).
- Monitor performance metrics to select a winner.

### 6. Security Scanning
Automated checks during the promotion process:
- **Secret Detection**: Blocks prompts containing API keys or passwords.
- **Unsafe Instructions**: Detects attempts to bypass filters or system instructions.

## API Usage

### Create a Template
```bash
POST /api/v1/admin/prompts/
{
  "name": "customer_greeting",
  "variable_schema": {
    "type": "object",
    "properties": {
      "name": {"type": "string"}
    }
  }
}
```

### Create a Version
```bash
POST /api/v1/admin/prompts/{id}/versions
{
  "content": "Hello {{name}}, how can I help you today?",
  "version_tag": "v1"
}
```

### Run Playground
```bash
POST /api/v1/admin/prompts/{id}/playground
{
  "version_id": "{version_id}",
  "variables": {"name": "Alice"}
}
```

### Promote to Production
```bash
POST /api/v1/admin/prompts/{id}/versions/{version_id}/promote?target_status=production
```
