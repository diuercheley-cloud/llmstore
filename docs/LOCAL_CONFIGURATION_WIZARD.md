---
owner: platform-ops
status: consolidated
---

# Local Configuration Wizard

The `configure-local-wizard.sh` script provides a guided, interactive way to configure the LLM Inference Stack for local appliance mode. It helps you set up the environment without manually editing `.env` files.

## Features

- **Interactive Mode**: Asks step-by-step questions about your setup.
- **Non-Interactive Mode**: Can be used with flags for automated deployments.
- **Security First**: 
  - Generates secure `ADMIN_TOKEN`.
  - Configures secure CORS defaults (localhost and 127.0.0.1).
  - Sets strict file permissions (600 for `.env.local`).
  - Masks secrets in reports.
- **Automatic Backups**: Creates a backup of your existing `.env.local` before making changes.
- **Configuration Summary**: Generates a JSON and Markdown summary of your settings.

## Usage

### Interactive (Recommended)

```bash
make configure-local
# OR
./scripts/configure-local-wizard.sh
```

### Non-Interactive (Automated)

```bash
make configure-local-noninteractive
# OR
./scripts/configure-local-wizard.sh --non-interactive --yes --base-url http://my-app.local --gpu
```

## Available Options

- `--interactive`: Run in interactive mode (default).
- `--non-interactive`: Run in non-interactive mode.
- `--yes`: Skip confirmations in non-interactive mode.
- `--dry-run`: Show what would be done without doing it.
- `--base-url URL`: Set public base URL (default: http://localhost:18080).
- `--host-port PORT`: Set host port (default: 18080).
- `--gpu`: Enable GPU mode.
- `--cpu-only`: Enable CPU-only mode.
- `--enable-demo`: Enable local demo mode.
- `--disable-demo`: Disable local demo mode.
- `--admin-email EMAIL`: Set admin email.

## Output

After running the wizard, you will find:
- `.env.local`: Updated environment variables.
- `.local/backups/env/`: Backups of previous `.env.local` files.
- `.local/install/configuration-summary.md`: A readable summary of the configuration.
- `.local/install/configuration-summary.json`: A machine-readable summary.

## Integration

The configuration wizard is designed to be run before `make install-local` or `make first-run`.

```bash
make configure-local
make install-local
```
