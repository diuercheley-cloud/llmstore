import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from validate_naming_consistency import validate_naming_consistency


def test_naming_consistency_audit():
    """
    Validates that the codebase uses standardized terminology.
    """
    # This is currently non-blocking
    assert validate_naming_consistency() is True
