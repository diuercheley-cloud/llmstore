# Prompt Template Engine

## Overview

The Prompt Template Engine transforms raw agent `instructions` into **versioned,
parametrizable, testable assets**. Agents can reference a prompt template instead
of embedding their system prompt directly.

## Key Concepts

### Template
A Jinja2-like text template with `{{ variable }}` placeholders. Templates are stored
separately from agent definitions and can be reused across agents.

### Variable Declaration
Variables must be declared with a name, type, required flag, default value, and
description. This ensures:
- Templates are self-documenting
- Missing variables fail early
- Variable values are validated before rendering
- Secret-like values (API keys, tokens) are blocked

### Versioning
Each template version is **immutable** — once created, the content cannot change.
Versions follow a promotion pipeline:

```
draft → staging → production
```

- **draft**: Initial state, editable (via new version)
- **staging**: Validated and security-scanned, ready for testing
- **production**: Promoted from staging only, used by agents
- **archived**: No longer active

### Render Events
Every template render is recorded with:
- `variables_hash` — SHA-256 of the variables used
- `output_hash` — SHA-256 of the rendered output
- `rendered_content_hash` — SHA-256 of template + variables
- `agent_run_id` — optional link to the AgentRun
- `agent_id` — optional link to the AgentDefinition

## Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `PROMPT_TEMPLATES_ENABLED` | `false` | Enable the template engine |
| `PROMPT_TEMPLATE_PLAYGROUND_ENABLED` | `false` | Enable the playground |

## Data Model

### Tables

| Table | Purpose |
|-------|---------|
| `prompt_templates` | Template container (existing) |
| `prompt_template_versions` | Immutable version snapshots (existing) |
| `prompt_template_variables` | Declared variable definitions (new) |
| `prompt_template_render_events` | Render audit trail (new) |

### prompt_template_variables

| Field | Type | Description |
|-------|------|-------------|
| `name` | `string` | Variable name (must be valid Python identifier) |
| `var_type` | `string` | `string`, `number`, `boolean`, `object`, `array`, `any` |
| `required` | `boolean` | Whether the variable must be provided |
| `default` | `text` | Default value if not provided |
| `description` | `text` | Human-readable description |

## Security

### Sandbox
Templates use Jinja2's `SandboxedEnvironment` which blocks:
- Access to arbitrary Python objects (`__class__`, `__bases__`, etc.)
- `eval()` / `exec()` calls
- File system access
- Import statements

### Secret Detection
Variable values matching these patterns are **blocked**:
- `sk-`, `pk-`, `whsec_`, `wh_` prefixes (API keys)
- Strings of 32+ characters (likely tokens)

Variable names matching these are **blocked**:
- `eval`, `exec`, `__import__`, `open`, `system`, `globals`, `locals`,
  `compile`, `__builtins__`, `__class__`, `__bases__`, `__subclasses__`

### Content Scanning
Template content is scanned for:
- Hardcoded API keys, passwords, secrets (warning)
- Prompt injection patterns (warning)
- Unsafe instructions like "ignore previous instructions" (warning)

## API Endpoints

All endpoints require admin auth and `PROMPT_TEMPLATES_ENABLED=true`.

### Create Template
```http
POST /api/v1/admin/prompts/templates
Content-Type: application/json

{
  "name": "customer-support-agent",
  "description": "Template for customer support agents"
}
```

### Declare Variable
```http
POST /api/v1/admin/prompts/templates/{id}/variables
Content-Type: application/json

{
  "name": "user_input",
  "var_type": "string",
  "required": true,
  "default": null,
  "description": "The user's question"
}
```

### Create Version
```http
POST /api/v1/admin/prompts/templates/{id}/versions
Content-Type: application/json

{
  "content": "You are a support agent for {{ company_name }}.\n\nUser question: {{ user_input }}",
  "version_tag": "v1"
}
```

### Render Template
```http
POST /api/v1/admin/prompts/templates/{id}/render
Content-Type: application/json

{
  "version_id": "uuid",
  "variables": {
    "company_name": "Acme Corp",
    "user_input": "How do I reset my password?"
  }
}
```

Response:
```json
{
  "version_id": "uuid",
  "version_tag": "v1",
  "rendered": "You are a support agent for Acme Corp...",
  "variables_hash": "abc123...",
  "output_hash": "def456..."
}
```

### Playground
```http
POST /api/v1/admin/prompts/templates/{id}/playground
Content-Type: application/json

{
  "version_id": "uuid",
  "variables": { "name": "World" }
}
```

### Promote Version
```http
POST /api/v1/admin/prompts/templates/{id}/versions/{version_id}/promote
Content-Type: application/json

{
  "target_status": "staging"
}
```

### Rollback
```http
POST /api/v1/admin/prompts/templates/{id}/rollback
Content-Type: application/json

{
  "to_version_id": "uuid"
}
```

### Validate Content
```http
POST /api/v1/admin/prompts/validate
Content-Type: application/json

{
  "content": "Hello {{ name }}!"
}
```

### Render Events
```http
GET /api/v1/admin/prompts/templates/{id}/render-events?limit=100
```

## Agent Integration

When `PROMPT_TEMPLATES_ENABLED=true` and an `AgentDefinition` has a
`prompt_template_id`, the AgentExecutor will:

1. Fetch the active version (or the specified `prompt_template_version_id`)
2. Resolve declared variables
3. Inject runtime variables (`input`, `agent_name`, `tools`, `tenant_id`,
   `user_id`)
4. Render the template into `instructions`
5. Record a `PromptTemplateRenderEvent`

### Variables Passed to Templates

| Variable | Source | Description |
|----------|--------|-------------|
| `input` | `run.input_text` | The user's input text |
| `agent_name` | `agent_def.name` | Agent name |
| `agent_description` | `agent_def.description` | Agent description |
| `tools` | `agent_def.allowed_tools` | Available tools as string |
| `tenant_id` | `run.tenant_id` | Tenant identifier |
| `user_id` | `run.user_id` | User identifier |

## Example Workflow

```python
# 1. Create template
template = await svc.create_template("tenant-1", "support-agent")

# 2. Declare variables
await svc.declare_variable(template.id, "user_input", "string", required=True)
await svc.declare_variable(template.id, "company_name", "string",
    required=True, default="Acme Corp")

# 3. Create version
version = await svc.create_version(
    template.id,
    content="You are {{ company_name }} support. Question: {{ user_input }}",
    created_by="admin@example.com",
    version_tag="v1",
)

# 4. Promote to production
await versioning.promote_to_staging(version.id)
await versioning.promote_to_production(version.id)
await svc.set_active_version(template.id, version.id)

# 5. Link to agent definition
agent_def.prompt_template_id = template.id
agent_def.prompt_template_version_id = version.id
```
