#!/usr/bin/env python3
import os
import subprocess
import sys

REQUIRED_FILES = [
    "LICENSE",
    "CODE_OF_CONDUCT.md",
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    ".github/CODEOWNERS"
]

FORBIDDEN_PATTERNS = [
    "*.bak",
    "*.log",
    ".env.local.bak",
    "venv/",
    ".venv/"
]

REQUIRED_BADGES = [
    "![CI]",
    "![Security Scan]",
    "![License]",
    "![Version]"
]

def check_required_files():
    missing = []
    for f in REQUIRED_FILES:
        if not os.path.exists(f):
            missing.append(f)
    return missing

def check_readme_badges():
    if not os.path.exists("README.md"):
        return ["README.md missing"]
    
    with open("README.md") as f:
        content = f.read()
    
    missing_badges = []
    for badge in REQUIRED_BADGES:
        if badge not in content:
            missing_badges.append(badge)
    return missing_badges

def check_forbidden_files():
    # Use git ls-files to see what is actually versioned
    try:
        res = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
        versioned_files = res.stdout.splitlines()
    except subprocess.CalledProcessError:
        print("Error: Not a git repository or git not found.")
        return ["Git error"]

    found_forbidden = []
    for f in versioned_files:
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.endswith("/") and f.startswith(pattern) or pattern.startswith("*.") and f.endswith(pattern[1:]) or f == pattern:
                found_forbidden.append(f)
                
    return found_forbidden

def main():
    print("==> Validating Release Readiness...")
    failed = False

    missing_files = check_required_files()
    if missing_files:
        print(f"FAILED: Missing mandatory files: {', '.join(missing_files)}")
        failed = True
    else:
        print("OK: All mandatory files present.")

    missing_badges = check_readme_badges()
    if missing_badges:
        print(f"FAILED: Missing README badges: {', '.join(missing_badges)}")
        failed = True
    else:
        print("OK: Essential README badges found.")

    forbidden = check_forbidden_files()
    if forbidden:
        print(f"FAILED: Forbidden files found in git history: {', '.join(forbidden[:10])}")
        if len(forbidden) > 10:
            print(f"... and {len(forbidden) - 10} more.")
        failed = True
    else:
        print("OK: No versioned garbage files found.")

    if failed:
        sys.exit(1)
    
    print("\nRelease readiness validation passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
