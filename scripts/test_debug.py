import os
import sys
# Simulate pytest environment for conftest
# In pytest, conftest.py in subdirectories are loaded
# control_plane/tests/conftest.py might be interfering
# Check if that file exists
print(f"control_plane/tests/conftest.py exists: {os.path.exists('control_plane/tests/conftest.py')}")
import control_plane.tests.conftest
from app.core.config import get_settings
print(f"Env: {os.environ.get('AGENT_RUNTIME_ENABLED')}")
s = get_settings()
print(f"Runtime: {s.agent_runtime_enabled}")
