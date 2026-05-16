import os
import sys
import re

def validate_framework_patterns():
    print("Validating framework patterns and searching for deprecated calls...")
    
    # Patterns to flag as deprecated/legacy
    deprecated_patterns = [
        (r'\.utcnow\(', "Use datetime.now(datetime.UTC) instead of .utcnow()"),
        (r'from pydantic import .*BaseModel', "Check Pydantic V2 migration status if needed"),
        (r're\.compile\(r"[^"]*\\"', "Check for deprecated regex escape sequences")
    ]
    
    root_dir = os.path.join(os.path.dirname(__file__), "..", "control_plane")
    found_issues = 0
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    for pattern, msg in deprecated_patterns:
                        if re.search(pattern, content):
                            print(f"WARNING: {msg} in {path}")
                            found_issues += 1
                            
    print(f"\nFramework validation complete. Found {found_issues} potential legacy patterns.")
    # For now, we don't fail the script, just report.
    return True

if __name__ == "__main__":
    validate_framework_patterns()
