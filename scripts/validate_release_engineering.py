import os
import sys

def check_file_exists(path):
    if not os.path.exists(path):
        print(f"MISSING: {path}")
        return False
    print(f"PRESENT: {path}")
    return True

def main():
    print("Validating release engineering baseline...")
    
    required_files = [
        "CHANGELOG.md",
        "docs/releases/release_process.md",
        "docs/releases/release_governance.md",
        "docs/releases/versioning_and_baselines.md",
        "control_plane/app/models/governance/release_baseline.py",
        "scripts/generate_release_baseline.py",
        "scripts/validate_release_engineering.py"
    ]
    
    success = True
    for f in required_files:
        if not check_file_exists(f):
            success = False
            
    # Check for prohibited claims/patterns
    prohibited_patterns = [
        "GITHUB_ACTIONS",
        "CI_PIPELINE",
        "DEPLOY_TO_CLOUD"
    ]
    
    # Simple check in scripts for prohibited patterns
    with open("scripts/generate_release_baseline.py", "r") as f:
        content = f.read()
        for p in prohibited_patterns:
            if p in content:
                print(f"PROHIBITED PATTERN FOUND: {p} in scripts/generate_release_baseline.py")
                success = False
                
    if success:
        print("\nRelease engineering validation PASSED.")
        sys.exit(0)
    else:
        print("\nRelease engineering validation FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
