import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from validate_v1_readiness import validate_v1_readiness

def test_v1_readiness_audit():
    """
    Verifies that the platform meets all v1 readiness criteria.
    """
    assert validate_v1_readiness() is True
