import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from validate_internal_security_review import validate_internal_security

def test_internal_security_audit():
    """
    Verifies that no common security anti-patterns exist in the codebase.
    """
    assert validate_internal_security() is True
