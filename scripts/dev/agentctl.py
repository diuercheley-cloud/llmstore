#!/usr/bin/env python3
import os
import sys

# Ensure project root is in path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.agentctl_pkg.cli import AgentCTL

if __name__ == "__main__":
    ctl = AgentCTL()
    ctl.run()
