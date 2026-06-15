#!/usr/bin/env python3
"""Backward-compatible entrypoint for ADR validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.validators.validate_adrs import *  # noqa: F401,F403,E402

if __name__ == "__main__":
    from scripts.validators.validate_adrs import main  # noqa: E402

    raise SystemExit(main())
