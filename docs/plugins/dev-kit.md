# Plugin Dev Kit (PDK)

The Plugin Dev Kit provides the tools and schemas needed to build platform-compatible plugins.

## Components

### 1. Plugin Manifest Schema
Every plugin must include a `plugin.json` manifest defining its tools and required permissions.

### 2. Local Test Harness
Test your tools in a simulated environment before uploading.
```python
from app.services.plugins.dev_kit import PluginHarness

harness = PluginHarness("plugin.json")
harness.validate()
harness.dry_run_tool("my_tool", {"arg1": "val1"})
```

### 3. Sandbox Dry-run
The PDK includes a sandbox wrapper to verify that your tool logic respects platform constraints (no network, limited FS).

### 4. Signature Helper
Utilities for signing your plugin bundles to ensure integrity and provenance.
