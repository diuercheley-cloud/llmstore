#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validators.validate_invariants import *  # noqa: F403,E402

if __name__ == "__main__":
    from validators.validate_invariants import main  # noqa: E402

    raise SystemExit(main())
