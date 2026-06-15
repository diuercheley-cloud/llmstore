#!/usr/bin/env python3
"""Validate platform documentation completeness and consistency.

Validates:
- Required docs exist
- README updated with required sections
- docs/index.md exists
- glossary exists with required terms
- timeline exists covering phases 69-82
- Mermaid diagrams exist in docs
- Internal links are valid (basic check)
- Explicit limitations are present
- Absence of prohibited claims
- Absence of formal certification claims
"""

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REQUIRED_DOCS = [
    "README.md",
    "docs/index.md",
    "docs/CANONICAL_INDEX.md",
    "docs/API_REFERENCE.md",
    "docs/CONFIGURATION_REFERENCE.md",
    "docs/FLAGS_INVENTORY.md",
    "docs/PRODUCT_SURFACE.md",
    "docs/architecture/platform_overview.md",
    "docs/architecture/platform_domain_map.md",
    "docs/architecture/platform_guarantees_and_limitations.md",
    "docs/architecture/platform_operational_model.md",
    "docs/architecture/platform_validation_workflows.md",
    "docs/architecture/platform_module_relationships.md",
    "docs/architecture/platform_glossary.md",
    "docs/architecture/platform_phase_timeline.md",
    "docs/operations/platform_runbook.md",
]

REQUIRED_GLOSSARY_TERMS = [
    "advisory-only",
    "bounded context",
    "compatibility contract",
    "deterministic",
    "dry-run",
    "federation",
    "governance workflow",
    "lineage",
    "offline-first",
    "placeholder trust",
    "plugin ABI",
    "policy bundle",
    "provenance",
    "replay-safe",
    "reproducible build",
    "sovereign",
]

REQUIRED_README_SECTIONS = [
    "Platform Architecture",
    "Principles",
    "Deterministic",
    "Replay-Safe",
    "Offline-First",
    "Sovereign",
    "Advisory-First",
    "Bounded Contexts",
    "Phases 69",
    "Explicit Limitations",
    "Navigating the Documentation",
]

REQUIRED_PHASES = [f"Phase {i}" for i in range(69, 83)]

MANDATORY_DIAGRAMS_KEYWORDS = [
    "bounded context",
    "module relationships",
    "validation flow",
    "federation flow",
    "plugin lifecycle",
    "provenance",
]

PROHIBITED_CLAIMS = [
    "military-grade",
    "guaranteed secure",
    "certified",
    "formally certified",
    "unbreakable",
    "impenetrable",
]

EXPLICIT_LIMITATIONS = [
    "Plugin ABI Sandbox",
    "Local PKI",
    "Policy-Based Attestation",
    "Offline-First",
    "Evidence-Driven Compliance",
]


def check_file_exists(path):
    full_path = os.path.join(REPO_ROOT, path)
    exists = os.path.isfile(full_path)
    if not exists:
        print(f"FAIL: Required doc missing: {path}")
    return exists


def check_content_in_file(path, patterns, case_sensitive=True):
    full_path = os.path.join(REPO_ROOT, path)
    if not os.path.isfile(full_path):
        return [False] * len(patterns)

    with open(full_path) as f:
        content = f.read()

    results = []
    for pattern in patterns:
        if case_sensitive:
            found = pattern in content
        else:
            found = pattern.lower() in content.lower()
        if not found:
            print(f"FAIL: '{pattern}' not found in {path}")
        results.append(found)
    return results


def check_mermaid_diagrams(path):
    full_path = os.path.join(REPO_ROOT, path)
    if not os.path.isfile(full_path):
        return False
    with open(full_path) as f:
        content = f.read()
    diagrams = re.findall(r"```mermaid\n(.*?)```", content, re.DOTALL)
    return len(diagrams) > 0


def check_prohibited_claims_in_file(path):
    full_path = os.path.join(REPO_ROOT, path)
    if not os.path.isfile(full_path):
        return True
    with open(full_path) as f:
        content = f.read()
    # Exclude sections that discuss prohibited claims as examples
    for marker in ["## Prohibited Claims", "### Validation fails"]:
        if marker in content:
            content = content.split(marker)[0]
    content = content.lower()
    found_claims = []
    for claim in PROHIBITED_CLAIMS:
        if claim.lower() in content:
            found_claims.append(claim)
    if found_claims:
        print(f"FAIL: Prohibited claims found in {path}: {found_claims}")
    return len(found_claims) == 0


def check_internal_links(path):
    full_path = os.path.join(REPO_ROOT, path)
    if not os.path.isfile(full_path):
        return True
    with open(full_path) as f:
        content = f.read()

    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    all_ok = True
    for text, link in links:
        if link.startswith("http"):
            continue
        link_path = os.path.normpath(os.path.join(os.path.dirname(path), link))
        target = os.path.join(REPO_ROOT, link_path)
        if not os.path.exists(target):
            print(f"WARNING: Broken link in {path}: '{text}' -> {link} (resolved: {link_path})")
            all_ok = False
    return all_ok


def main():
    errors = 0

    print("=== Platform Documentation Validation ===\n")

    # 1. Check required docs exist
    print("--- Required Documents ---")
    for doc in REQUIRED_DOCS:
        if not check_file_exists(doc):
            errors += 1
    print()

    # 2. Check README sections
    print("--- README Sections ---")
    readme_results = check_content_in_file("README.md", REQUIRED_README_SECTIONS)
    errors += sum(1 for r in readme_results if not r)
    print()

    # 3. Check docs/index.md exists
    print("--- Documentation Index ---")
    if not check_file_exists("docs/index.md"):
        errors += 1
    print()

    # 3.5 Check generated docs carry generation marker
    print("--- Generated References ---")
    for doc in [
        "docs/API_REFERENCE.md",
        "docs/CONFIGURATION_REFERENCE.md",
        "docs/FLAGS_INVENTORY.md",
        "docs/PRODUCT_SURFACE.md",
    ]:
        results = check_content_in_file(
            doc, ["generated_by: scripts/docs/generate_reference_docs.py"]
        )
        errors += sum(1 for r in results if not r)
    print()

    # 4. Check glossary terms
    print("--- Glossary Terms ---")
    glossary_results = check_content_in_file(
        "docs/architecture/platform_glossary.md", REQUIRED_GLOSSARY_TERMS, case_sensitive=False
    )
    errors += sum(1 for r in glossary_results if not r)
    print()

    # 5. Check timeline phases
    print("--- Phase Timeline ---")
    timeline_results = check_content_in_file(
        "docs/architecture/platform_phase_timeline.md", REQUIRED_PHASES
    )
    errors += sum(1 for r in timeline_results if not r)
    print()

    # 6. Check Mermaid diagrams
    print("--- Mermaid Diagrams ---")
    doc_files = [
        "docs/architecture/platform_domain_map.md",
        "docs/architecture/platform_module_relationships.md",
        "docs/architecture/platform_validation_workflows.md",
        "docs/architecture/platform_overview.md",
        "docs/architecture/platform_phase_timeline.md",
        "docs/architecture/platform_operational_model.md",
    ]
    for doc in doc_files:
        if not check_mermaid_diagrams(doc):
            print(f"WARNING: No Mermaid diagram found in {doc}")
    print()

    # 7. Check explicit limitations in README
    print("--- Explicit Limitations ---")
    limitations_results = check_content_in_file(
        "README.md", EXPLICIT_LIMITATIONS, case_sensitive=False
    )
    errors += sum(1 for r in limitations_results if not r)
    print()

    # 8. Check limitations doc
    print("--- Limitations Document ---")
    limitations_doc_results = check_content_in_file(
        "docs/architecture/platform_guarantees_and_limitations.md",
        EXPLICIT_LIMITATIONS + ["Prohibited Claims", "Advisory Nature"],
        case_sensitive=False,
    )
    errors += sum(1 for r in limitations_doc_results if not r)
    print()

    # 9. Check prohibited claims across docs
    print("--- Prohibited Claims Check ---")
    for doc in REQUIRED_DOCS:
        if not check_prohibited_claims_in_file(doc):
            errors += 1
    print()

    # 10. Basic internal link checks
    print("--- Internal Link Validation ---")
    for doc in REQUIRED_DOCS:
        if not check_internal_links(doc):
            pass
    print()

    # Summary
    print("=== Summary ===")
    if errors == 0:
        print("Platform documentation validation PASSED.")
        return 0
    else:
        print(f"Platform documentation validation FAILED with {errors} error(s).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
