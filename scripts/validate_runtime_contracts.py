#!/usr/bin/env python3
"""Backward-compatible entrypoint for runtime contract validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.validators.validate_runtime_contracts import *  # noqa: F401,F403,E402

if __name__ == "__main__":
    from scripts.validators.validate_runtime_contracts import main  # noqa: E402

    raise SystemExit(main())
