# Release Bundle Local

This document describes how to generate a secure, distributable release bundle of the `llm-inference-stack`.

## Overview

The release bundle is a compressed `.tar.gz` archive containing only the necessary files to deploy the stack on another machine. It explicitly excludes:
- Sensitive data (`.env`, `.local/`, backups, exports)
- Large assets (GGUF models)
- Development artifacts (`.git/`, `.venv/`, `node_modules/`, caches)
- Secrets (verified via `scripts/check-secrets.sh`)

## Generating a Bundle

Use the `scripts/create-release-bundle.sh` script or the Makefile target.

### Using Makefile (Recommended)

```bash
make release-bundle
```

This will use the version defined in the `VERSION` file and include docs, examples, and the demo.

### Using the Script Directly

```bash
./scripts/create-release-bundle.sh --version v1.5.2 --include-docs --include-examples --include-demo
```

#### Options:
- `--version vX.Y.Z`: (Required) The version string for the bundle.
- `--output-dir <dir>`: Directory to save the bundle (default: `releases/`).
- `--include-docs`: Include the `docs/` directory.
- `--include-examples`: Include the `examples/` directory.
- `--include-demo`: Include the `demo/` directory.
- `--dry-run`: Perform all steps except creating the final archive.

## Output

The script generates the following files in `releases/<version>/`:
1. `llm-inference-stack-<version>.tar.gz`: The compressed bundle.
2. `bundle-manifest.json`: Metadata about the bundle (git commit, inclusions/exclusions, etc.).
3. `bundle-checksums.sha256`: SHA256 checksum of the archive.

## Validation

To ensure the bundle is correct and secure, run:

```bash
./scripts/validate-release-bundle.sh
```

This script will:
- Create a test bundle.
- Extract it and verify forbidden files are absent.
- Validate the manifest and checksums.
- Run a secrets scan on the extracted content.

## Security

The bundling process includes a mandatory secrets scan on the staging directory. If any potential secret is detected (e.g., hardcoded API keys in the source code), the process will abort.

**Note:** Always ensure your `.env` and `.env.local` files are NOT in the staging area. The script handles this automatically by excluding them from the copy list and deleting them if they somehow end up in staging.
