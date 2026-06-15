#!/usr/bin/env python3
import json
import os
import sys
import xml.etree.ElementTree as ET

CORE_AREAS = {
    "core_runtime": [
        "app/services/runtime",
        "app/services/workflows",
        "app/services/agents",
        "app/services/routing",
    ],
    "governance": ["app/services/governance"],
    "security": ["app/services/security", "app/services/auth"],
    "financial/billing": ["app/services/billing"],
}

MIN_GATE = 70.0
RATCHET_FILE = "config/coverage-ratchets.json"


def main():
    coverage_file = "coverage.xml"
    if not os.path.exists(coverage_file):
        coverage_file = "control_plane/coverage.xml"
    if not os.path.exists(coverage_file):
        print(
            "ERROR: coverage.xml or control_plane/coverage.xml not found. Please run tests with coverage first."
        )
        sys.exit(1)

    tree = ET.parse(coverage_file)
    root = tree.getroot()

    # Parse all classes in coverage.xml
    files_cov = {}
    for class_node in root.findall(".//class"):
        filename = class_node.get("filename")
        lines_valid = 0
        lines_hit = 0

        lines_node = class_node.find("lines")
        if lines_node is not None:
            for line in lines_node.findall("line"):
                lines_valid += 1
                if int(line.get("hits", 0)) > 0:
                    lines_hit += 1
        else:
            lines_valid = int(class_node.get("lines-valid", 0))
            lines_hit = int(class_node.get("lines-hit", 0))

        files_cov[filename] = {"valid": lines_valid, "hit": lines_hit}

    # Aggregate by core area
    area_stats = {}
    for area, paths in CORE_AREAS.items():
        total_valid = 0
        total_hit = 0
        for filepath, data in files_cov.items():
            # Check if filepath starts with any of the path prefixes
            if any(filepath.startswith(p) for p in paths):
                total_valid += data["valid"]
                total_hit += data["hit"]

        coverage = (total_hit / total_valid * 100) if total_valid > 0 else 100.0
        area_stats[area] = {"valid": total_valid, "hit": total_hit, "coverage": coverage}

    # Load ratchet plan if exists
    ratchets = {}
    if os.path.exists(RATCHET_FILE):
        try:
            with open(RATCHET_FILE, encoding="utf-8") as f:
                ratchets = json.load(f)
        except Exception as e:
            print(f"Warning: failed to load {RATCHET_FILE}: {e}")

    failed = False
    print("=== Core Coverage Gates Report ===")
    for area, stats in area_stats.items():
        cov = stats["coverage"]
        required = ratchets.get(area, MIN_GATE)
        print(f"Area: {area}")
        print(f" - Coverage: {stats['hit']}/{stats['valid']} ({cov:.2f}%)")
        print(f" - Required: {required:.2f}%")

        if cov < required:
            print(f" - STATUS: FAILED (under target of {required:.2f}%)")
            failed = True
        else:
            print(" - STATUS: PASSED")

    if failed:
        print("\nFAILURE: One or more core areas did not satisfy coverage gates.")
        sys.exit(1)
    else:
        print("\nSUCCESS: All core area coverage gates passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
