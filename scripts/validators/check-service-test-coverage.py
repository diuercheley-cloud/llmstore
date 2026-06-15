#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from datetime import datetime

SERVICES_DIR = "control_plane/app/services"
TEST_ROOTS = ("tests", "tests/control_plane")
REPORT_PATH = "artifacts/service-test-coverage-report.json"
MAINTENANCE_BUDGETS_PATH = "config/maintenance-budgets.json"

# Priority classification mapping
P0_KEYWORDS = [
    "runtime",
    "workflows",
    "agents",
    "security",
    "auth",
    "rbac",
    "plugins",
    "rag",
    "memory",
    "context",
    "connector",
    "iam",
]
P1_KEYWORDS = [
    "observability",
    "readiness",
    "operator",
    "operations",
    "platform",
    "monitoring",
    "metrics",
]
P2_KEYWORDS = [
    "admin",
    "support",
    "docs",
    "billing",
    "compliance",
    "governance",
    "payment",
    "notifications",
    "providers",
    "models",
    "inference",
    "routing",
    "mesh",
    "cache",
    "invariants",
]


def get_priority(path):
    path_lower = path.lower()

    filename = os.path.basename(path_lower)
    if filename in ["auth.py", "admin_rbac.py", "context_manager.py"]:
        return "P0"
    if filename in ["managed_metrics.py", "visual_observability.py", "platform_slo.py"]:
        return "P1"
    if filename in ["support_bundle.py", "admin_model_management.py", "branding.py"]:
        return "P2"

    parts = path_lower.split(os.sep)
    for part in parts:
        if any(k in part for k in P0_KEYWORDS):
            return "P0"
        if any(k in part for k in P1_KEYWORDS):
            return "P1"
        if any(k in part for k in P2_KEYWORDS):
            return "P2"

    return "P2"


def list_services():
    services = []
    for root, dirs, files in os.walk(SERVICES_DIR):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                full_path = os.path.join(root, file)
                services.append(full_path)
    return services


def list_changed_services():
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", SERVICES_DIR],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return []

    changed = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if path.endswith(".py") and os.path.isfile(path) and "__init__.py" not in path:
            changed.append(path)
    return sorted(set(changed))


def find_test(service_path):
    service_name = os.path.basename(service_path).replace(".py", "")
    module_hint = service_path.replace("/", ".").replace(".py", "")

    patterns = [
        f"test_{service_name}.py",
        f"test_{service_name}_api.py",
        f"test_{service_name}_service.py",
        f"test_{service_name}_endpoint.py",
    ]

    for test_root in TEST_ROOTS:
        if not os.path.isdir(test_root):
            continue
        for root, dirs, files in os.walk(test_root):
            for file in files:
                file_lower = file.lower()
                test_path = os.path.join(root, file)
                if any(p.lower() == file_lower for p in patterns):
                    return test_path
                if f"test_{service_name.lower()}" in file_lower:
                    return test_path
                if not file.endswith(".py"):
                    continue
                try:
                    with open(test_path, encoding="utf-8") as handle:
                        content = handle.read()
                except OSError:
                    continue
                if module_hint in content or service_name in content:
                    return test_path

    return None


def main():
    services = list_services()
    changed_services = list_changed_services()
    results = {
        "P0": {"total": 0, "tested": 0, "untested": []},
        "P1": {"total": 0, "tested": 0, "untested": []},
        "P2": {"total": 0, "tested": 0, "untested": []},
    }
    changed_results = {
        "P0": {"total": 0, "tested": 0, "untested": []},
        "P1": {"total": 0, "tested": 0, "untested": []},
        "P2": {"total": 0, "tested": 0, "untested": []},
    }

    service_test_map = {}

    for service in services:
        priority = get_priority(service)
        test = find_test(service)

        results[priority]["total"] += 1
        if test:
            results[priority]["tested"] += 1
            service_test_map[service] = test
        else:
            results[priority]["untested"].append(service)
            service_test_map[service] = None

        if service in changed_services:
            changed_results[priority]["total"] += 1
            if test:
                changed_results[priority]["tested"] += 1
            else:
                changed_results[priority]["untested"].append(service)

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "scope": {
            "changed_services": changed_services,
            "gate_priorities": ["P0", "P1"],
        },
        "overall": {
            "total": sum(results[p]["total"] for p in results),
            "tested": sum(results[p]["tested"] for p in results),
        },
        "by_priority": results,
        "changed_by_priority": changed_results,
        "mapping": service_test_map,
    }

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    # Print report to stdout
    print("# Service Test Coverage Report\n")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    overall_total = report["overall"]["total"]
    overall_tested = report["overall"]["tested"]
    overall_coverage = (overall_tested / overall_total * 100) if overall_total > 0 else 100

    print(f"## Overall Coverage: {overall_tested}/{overall_total} ({overall_coverage:.2f}%)\n")

    if changed_services:
        changed_total = sum(changed_results[p]["total"] for p in changed_results)
        changed_tested = sum(changed_results[p]["tested"] for p in changed_results)
        changed_coverage = (changed_tested / changed_total * 100) if changed_total > 0 else 100
        print(
            f"## Changed Services Coverage: {changed_tested}/{changed_total} ({changed_coverage:.2f}%)\n"
        )

    for p in ["P0", "P1", "P2"]:
        total = results[p]["total"]
        tested = results[p]["tested"]
        coverage = (tested / total * 100) if total > 0 else 100
        print(f"### Priority {p}")
        print(f"- Coverage: {tested}/{total} ({coverage:.2f}%)")
        if results[p]["untested"]:
            print("- Untested Services:")
            # Show only top 10 to keep output clean, unless it's a small list
            untested = results[p]["untested"]
            for s in untested[:20]:
                print(f"  - {s}")
            if len(untested) > 20:
                print(f"  - ... and {len(untested) - 20} more.")
        print()

    if changed_services:
        print("## Changed Services Gate Scope\n")
        for p in ["P0", "P1", "P2"]:
            total = changed_results[p]["total"]
            tested = changed_results[p]["tested"]
            coverage = (tested / total * 100) if total > 0 else 100
            print(f"### Changed Priority {p}")
            print(f"- Coverage: {tested}/{total} ({coverage:.2f}%)")
            if changed_results[p]["untested"]:
                print("- Untested Services:")
                for service in changed_results[p]["untested"]:
                    print(f"  - {service}")
            print()

    # Exit code for gate
    if "--gate" in sys.argv:
        gate_untested = changed_results["P0"]["untested"] + changed_results["P1"]["untested"]
        if gate_untested:
            print("FAILURE: Untested changed core services found!")
            sys.exit(1)
        if os.path.exists(MAINTENANCE_BUDGETS_PATH):
            with open(MAINTENANCE_BUDGETS_PATH, encoding="utf-8") as handle:
                budgets = json.load(handle)
            historical_limits = {
                "P0": budgets.get("max_untested_p0_services"),
                "P1": budgets.get("max_untested_p1_services"),
            }
            exceeded = [
                f"{priority} untested services: {len(results[priority]['untested'])} > {limit}"
                for priority, limit in historical_limits.items()
                if limit is not None and len(results[priority]["untested"]) > limit
            ]
            if exceeded:
                print("FAILURE: Historical core-service coverage budget exceeded!")
                for failure in exceeded:
                    print(f" - {failure}")
                sys.exit(1)
        print("SUCCESS: All changed P0/P1 services have tests.")
        sys.exit(0)


if __name__ == "__main__":
    main()
