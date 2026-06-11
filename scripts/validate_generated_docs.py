import os
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
GEN_HEADER = "<!-- AUTO-GENERATED: do not edit manually -->"

REQUIRED_DOCS = [
    "docs/generated/CONFIGURATION_REFERENCE.md",
    "docs/generated/FLAGS_INVENTORY.md",
    "docs/generated/PROFILES_REFERENCE.md",
    "docs/generated/API_SURFACE.md",
    "docs/generated/STORAGE_BACKENDS.md",
    "docs/generated/BACKUP_CAPABILITIES.md",
    "docs/generated/PRODUCT_SURFACE.md"
]

def validate():
    errors = []
    for doc_path in REQUIRED_DOCS:
        full_path = root_dir / doc_path
        if not full_path.exists():
            errors.append(f"Missing generated doc: {doc_path}")
            continue
            
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
            if GEN_HEADER not in content:
                errors.append(f"Doc {doc_path} is missing the AUTO-GENERATED header.")
                
    if errors:
        print("Validation FAILED:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("All generated documents are valid.")
        sys.exit(0)

if __name__ == "__main__":
    validate()
