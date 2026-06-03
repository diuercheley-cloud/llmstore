import os
import sys

def fix_imports():
    """
    Ensure the project root is in PYTHONPATH so internal modules can be imported.
    """
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    
    # Also ensure scripts/llm_harness is accessible if needed as a package
    harness_dir = os.path.join(root_dir, "scripts")
    if harness_dir not in sys.path:
        sys.path.insert(0, harness_dir)

if __name__ == "__main__":
    fix_imports()
    print("PYTHONPATH fixed.")
