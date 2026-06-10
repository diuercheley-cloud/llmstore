"""
DEPRECATED: This module (scripts/llm_harness/agent_harness.py) is deprecated.
Please migrate to running code tasks via 'python3 -m scripts.llm_harness.cli'
or importing from 'scripts.llm_harness.legacy_runner'.
"""

import os
import sys

# Add project root to path to support direct script execution
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.llm_harness.legacy_runner import main, run_harness  # noqa: F401, E402

if __name__ == "__main__":
    main()
