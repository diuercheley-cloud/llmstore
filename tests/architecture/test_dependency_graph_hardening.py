import os
import sys

# Add scripts to path to reuse logic
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "validators"))
from validate_dependency_graph import validate_dependency_graph


def test_dependency_graph_invariants():
    """
    Ensures that the dependency graph follows architectural rules.
    """
    assert validate_dependency_graph() is True
