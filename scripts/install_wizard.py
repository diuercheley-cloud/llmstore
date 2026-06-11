from __future__ import annotations

import sys

from scripts.llm_harness.stack_cli import main

if __name__ == "__main__":
    raise SystemExit(main(["install", *sys.argv[1:]]))
