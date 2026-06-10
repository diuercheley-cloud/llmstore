# Agent Bundle Workflow

Complete developer flow: create, validate, test, sign, and publish agent bundles.

## Overview

```
init → validate → test → sign → publish
  │        │        │      │        │
  v        v        v      v        v
skeleton  checks  evals  ed25519  marketplace
```

## Shell Scripts

All scripts are in `scripts/`:

| Script | Purpose | Usage |
|--------|---------|-------|
| `agent-bundle-init.sh` | Create bundle skeleton | `./agent-bundle-init.sh <name> [dir]` |
| `agent-bundle-validate.sh` | Validate manifest + structure | `./agent-bundle-validate.sh [dir]` |
| `agent-bundle-test.sh` | Run eval suite + dry-run | `./agent-bundle-test.sh [dir]` |
| `agent-bundle-sign.sh` | Sign with ed25519 key | `./agent-bundle-sign.sh [dir] [keyfile]` |
| `agent-bundle-publish.sh` | Publish to marketplace | `./agent-bundle-publish.sh [dir]` |

## Bundle Structure

```
my-agent/
├── manifest.json          # Required: bundle manifest
├── bundle.sig             # After signing: signature file
├── src/
│   └── instructions.md    # Agent instructions
├── tests/
│   └── test_basic.py      # Unit tests
├── evals/
│   └── eval_cases.json    # Evaluation cases
├── .gitignore
└── README.md
```

## Manifest Schema

```json
{
  "name": "my-agent",
  "version": "1.0.0",
  "description": "What the agent does",
  "author": "Your Name",
  "category": "support|analytics|general|...",
  "min_platform_version": "1.7.0",
  "agent_definition": {
    "name": "Display Name",
    "instructions": "System prompt",
    "model_id": "gpt-4o",
    "allowed_tools": ["tool_name"]
  },
  "tool_requirements": [
    {"name": "tool_name", "version": "^1.0.0"}
  ],
  "memory_policy": {
    "type": "short_term",
    "retention_days": 7
  },
  "eval_suite": {
    "name": "Test Suite",
    "cases": [
      {"input": "user message", "expected_contains": "keyword"}
    ]
  },
  "checksums": {},
  "signature": {}
}
```

## Validation Checks

| Check | Required | Description |
|-------|----------|-------------|
| `manifest_parse` | Yes | Valid JSON |
| `name_present` | Yes | Bundle name exists |
| `version_present` | Yes | Semver version |
| `agent_definition` | Yes | Has instructions + model_id |
| `author_present` | No | Author name |
| `platform_version` | No | Min platform version |
| `tool_requirements` | No | Tool dependencies |
| `eval_suite` | No | Test cases |
| `signature` | Recommended | Ed25519 signature |

## Signing

- Algorithm: ed25519
- Key location: `~/.agentctl/keys/default_ed25519.pem`
- Signature file: `bundle.sig` (JSON with checksum, signature, public key, timestamp)
- Manifest gets embedded signature object

### Trust Policy
- External bundles: signature always required
- Internal bundles in production: signature required unless `allow_unsigned_internal_bundles=True`
- Internal bundles in development: optional

## Publishing

1. Bundle must pass validation
2. Signature recommended (required for marketplace)
3. Published as `draft` status
4. Platform review before going live
5. Creates `AgentBundleVersion` + `AgentMarketplaceEntry` records

## Frontend Pages

| Page | Route | Purpose |
|------|-------|---------|
| Bundles | `/developers/bundles` | Main bundle management page |
| BundleUpload | (component) | Drag-drop upload |
| BundleValidationReport | (component) | Validation results |
| BundleSigningGuide | (component) | Signing documentation |

## CLI Commands

```bash
# Initialize
agentctl bundle init my-agent

# Validate
./scripts/validators/agent-bundle-validate.sh ./my-agent

# Test
./scripts/dev/agent-bundle-test.sh ./my-agent

# Sign
./scripts/release/agent-bundle-sign.sh ./my-agent

# Publish
./scripts/dev/agent-bundle-publish.sh ./my-agent
```

## Tests

1. `init` creates directory with manifest.json, src/, tests/, evals/
2. `validate` fails without manifest.json
3. `validate` passes with valid manifest
4. `test` runs eval cases from manifest
5. `sign` generates ed25519 key if none exists
6. `sign` updates manifest with signature
7. `publish` creates draft marketplace entry
