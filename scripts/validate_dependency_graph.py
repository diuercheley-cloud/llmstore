import os
import sys
import re

def validate_dependency_graph():
    print("Validating architectural dependency graph...")
    
    # Rules: (Source Folder, Forbidden Patterns)
    rules = [
        ("app/services", [r"from app\.api(?!\.deps)", r"import app\.api(?!\.deps)"]),
        ("app/models", [r"from app\.services", r"import app\.services", r"from app\.api", r"import app\.api"]),
        ("app/db", [r"from app\.services", r"import app\.services", r"from app\.api", r"import app\.api", r"from app\.models", r"import app\.models"])
    ]
    
    root_dir = os.path.join(os.path.dirname(__file__), "..", "control_plane", "app")
    violations = 0
    
    for folder, forbidden in rules:
        folder_path = os.path.join(root_dir, folder.split("/")[-1])
        if not os.path.exists(folder_path):
            continue
            
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        for pattern in forbidden:
                            if re.search(pattern, content):
                                print(f"ARCHITECTURE VIOLATION: Illegal import {pattern} in {path}")
                                violations += 1
                                
    if violations > 0:
        print(f"\nDependency graph validation FAILED with {violations} violations.")
        return False
    
    print("\nDependency graph validation PASSED.")
    return True

if __name__ == "__main__":
    if not validate_dependency_graph():
        sys.exit(1)
