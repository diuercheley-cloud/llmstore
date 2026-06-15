import os
import sys
import xml.etree.ElementTree as ET


def main():
    if not os.path.exists("coverage.xml"):
        print("coverage.xml not found")
        sys.exit(1)

    tree = ET.parse("coverage.xml")
    root = tree.getroot()

    packages = {}

    # We want to group by package/directory under control_plane/app/services/
    # and control_plane/app/core/ etc.
    for class_node in root.findall(".//class"):
        filename = class_node.get("filename")
        line_rate = float(class_node.get("line-rate", 0))
        lines_valid = 0
        lines_hit = 0

        lines_node = class_node.find("lines")
        if lines_node is not None:
            for line in lines_node.findall("line"):
                lines_valid += 1
                if int(line.get("hits", 0)) > 0:
                    lines_hit += 1
        else:
            # Fallback if lines node is not present or empty
            lines_valid = int(class_node.get("lines-valid", 0))
            lines_hit = int(class_node.get("lines-hit", 0))

        # Group by directory prefix
        # e.g., control_plane/app/services/security/kms_runtime.py -> control_plane/app/services/security
        dir_name = os.path.dirname(filename)
        if dir_name not in packages:
            packages[dir_name] = {"valid": 0, "hit": 0, "files": []}

        packages[dir_name]["valid"] += lines_valid
        packages[dir_name]["hit"] += lines_hit
        packages[dir_name]["files"].append(
            {
                "name": os.path.basename(filename),
                "valid": lines_valid,
                "hit": lines_hit,
                "coverage": (lines_hit / lines_valid * 100) if lines_valid > 0 else 100,
            }
        )

    for pkg, data in sorted(packages.items()):
        total = data["valid"]
        hit = data["hit"]
        cov = (hit / total * 100) if total > 0 else 100
        print(f"{pkg}: {hit}/{total} ({cov:.2f}%)")


if __name__ == "__main__":
    main()
