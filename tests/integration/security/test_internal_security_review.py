import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts", "validators"))
from validate_internal_security_review import validate_internal_security


def test_internal_security_audit():
    """
    Verifies that no common security anti-patterns exist in the codebase.
    """
    assert validate_internal_security() is True
