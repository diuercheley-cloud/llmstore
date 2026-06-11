#!/usr/bin/env python3
"""Backward-compatible entrypoint for ADR validation."""

from scripts.validators.validate_adrs import *  # noqa: F401,F403


if __name__ == "__main__":
    from scripts.validators.validate_adrs import main

    raise SystemExit(main())
