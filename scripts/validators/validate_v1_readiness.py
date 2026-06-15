import os
import sys


def validate_v1_readiness():
    print("Validating v1 readiness criteria...")

    requirements = [
        ("CHANGELOG.md", "Changelog exists"),
        ("docs/quality/coverage_baseline.md", "Coverage baseline generated"),
        ("docs/performance/performance_baseline.md", "Performance baseline generated"),
        ("docs/security/internal_security_review.md", "Security review documentation exists"),
        ("docs/architecture/naming_consistency.md", "Naming consistency documentation exists"),
        ("docs/releases/latest_release_manifest.json", "Release baseline manifest generated"),
    ]

    missing = 0
    for path, msg in requirements:
        if not os.path.exists(path):
            print(f"FAILED: {msg} (Path not found: {path})")
            missing += 1
        else:
            print(f"PASSED: {msg}")

    if missing > 0:
        print(f"\nv1 Readiness validation FAILED. {missing} criteria not met.")
        return False

    print("\nv1 Readiness validation PASSED.")
    return True


if __name__ == "__main__":
    if not validate_v1_readiness():
        sys.exit(1)
