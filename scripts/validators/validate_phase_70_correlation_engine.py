import sys
from pathlib import Path

# --- Configuration ---
PHASE = "70"
COMPONENT = "Operations Correlation Engine"
CONTROL_PLANE_DIR = Path("control_plane")
APP_DIR = CONTROL_PLANE_DIR / "app"
MODELS_DIR = APP_DIR / "models"
API_DIR = APP_DIR / "api"
SERVICES_DIR = APP_DIR / "services"
DOCS_DIR = Path("docs")
TESTS_DIR = Path("tests")

REQUIRED_FILES = [
    MODELS_DIR / "operations" / "correlation.py",
    API_DIR / "operations_correlation_admin.py",
    API_DIR / "operations_correlation_portal.py",
    SERVICES_DIR / "operations" / "correlation" / "deterministic_correlation_engine.py",
    SERVICES_DIR / "operations" / "correlation" / "trust_graph.py",
    SERVICES_DIR / "operations" / "correlation" / "receipts.py",
    SERVICES_DIR / "operations" / "correlation" / "audit_events.py",
    DOCS_DIR / "operations" / "operations_correlation_engine.md",
]

PHASE_70_TESTS = [
    TESTS_DIR / "operations" / "test_correlation_models.py",
    TESTS_DIR / "operations" / "test_deterministic_correlation_engine.py",
    TESTS_DIR / "operations" / "test_operational_trust_graph.py",
    TESTS_DIR / "operations" / "test_correlation_api.py",
    TESTS_DIR / "operations" / "test_correlation_receipts.py",
    TESTS_DIR / "operations" / "test_correlation_audit_events.py",
    TESTS_DIR / "operations" / "test_correlation_risk_analysis.py",
    TESTS_DIR / "operations" / "test_correlation_dashboard.py",
    TESTS_DIR / "operations" / "test_phase_70_validation.py",
]

PROHIBITED_CLAIMS = [
    "PIX real ativo",
    "PSP real ativo",
    "ML externo obrigatório",
    "Conexão com nuvem obrigatória",
    "Deep learning não-determinístico",
]

GRAPH_DB_MARKERS = [
    "neo4j",
    "arangodb",
    "janusgraph",
    "gremlin",
    "networkx",
    "rdflib",
]

FORBIDDEN_RUNTIME_MARKERS = [
    "random.",
    "np.random",
    "torch.rand",
    "requests.",
    "httpx.",
    "aiohttp.",
    "openai.",
    "anthropic.",
    "google.generativeai",
    "sklearn.",
    "tensorflow.",
    "keras.",
]


def check_file_exists(path):
    if path.exists():
        print(f"  [OK] Found: {path}")
        return True
    else:
        print(f"  [FAIL] Missing: {path}")
        return False


def check_string_in_file(path, target_string, must_be_present=True):
    if not path.exists():
        return False
    content = path.read_text()
    found = target_string in content
    if found == must_be_present:
        print(f"  [OK] {'Found' if must_be_present else 'Not found'}: '{target_string}' in {path}")
        return True
    else:
        print(
            f"  [FAIL] {'Missing' if must_be_present else 'Forbidden'}: '{target_string}' in {path}"
        )
        return False


def read_file(path):
    return path.read_text() if path.exists() else ""


def validate_no_forbidden_markers(path, markers, label):
    content = read_file(path)
    if not content:
        return False
    for f in markers:
        if f in content:
            print(f"  [FAIL] {label}: '{f}' in {path}")
            return False
    print(f"  [OK] {label} validated in {path}")
    return True


def validate_advisory_only(path):
    content = read_file(path)
    if not content:
        return False
    forbidden = [
        "block_client",
        "suspend_account",
        "terminate_session",
        "apply_restriction",
        "auto_remediate",
    ]
    for marker in forbidden:
        if marker in content:
            print(f"  [FAIL] Forbidden remediation/enforcement marker found: '{marker}' in {path}")
            return False
    if "advisory_only=True" not in content and "advisory_only" not in content:
        print(f"  [FAIL] Missing advisory_only flag in {path}")
        return False
    print(f"  [OK] Advisory-only status validated in {path}")
    return True


def validate_dry_run(path):
    content = read_file(path)
    if not content:
        return False
    if "dry_run" not in content:
        print(f"  [FAIL] Missing dry_run evidence in {path}")
        return False
    print(f"  [OK] Dry-run behavior validated in {path}")
    return True


def validate_tenant_isolation():
    admin_path = API_DIR / "operations_correlation_admin.py"
    portal_path = API_DIR / "operations_correlation_portal.py"
    admin_content = read_file(admin_path)
    portal_content = read_file(portal_path)
    required_markers = [
        (
            "admin correlations filter by client_id",
            "OperationalCorrelation.client_id == client_id",
            admin_content,
        ),
        ("portal auth dependency", "require_client", portal_content),
        (
            "portal filter by authenticated client",
            "OperationalCorrelation.client_id == client.id",
            portal_content,
        ),
    ]
    success = True
    for label, marker, content in required_markers:
        if marker not in content:
            print(f"  [FAIL] Missing tenant isolation marker for {label}")
            success = False
        else:
            print(f"  [OK] Tenant isolation marker found for {label}")
    return success


def validate_route_registration():
    main_path = APP_DIR / "main.py"
    main_content = read_file(main_path)
    success = True
    for marker in [
        "operations_correlation_admin_router",
        "operations_correlation_portal_router",
        'prefix="/admin/operations/correlations"',
    ]:
        if marker not in main_content:
            print(f"  [FAIL] Missing route registration marker: {marker}")
            success = False
        else:
            print(f"  [OK] Route registration marker found: {marker}")
    return success


def main():
    print(f"--- Validating Phase {PHASE}: {COMPONENT} ---")
    success = True

    # 1. Structural Checks
    print("\n[1/5] Checking file structure...")
    for f in REQUIRED_FILES:
        if not check_file_exists(f):
            success = False
    for f in PHASE_70_TESTS:
        if not check_file_exists(f):
            success = False

    # 2. Migration Check
    print("\n[2/5] Checking migrations...")
    migration_found = any(
        f.name.endswith("phase70_correlation_engine.py")
        for f in (CONTROL_PLANE_DIR / "alembic" / "versions").glob("*.py")
    )
    if migration_found:
        print("  [OK] Phase 70 migration found.")
    else:
        print("  [FAIL] Phase 70 migration missing.")
        success = False

    # 3. Architectural Invariants
    print("\n[3/5] Validating architectural invariants...")
    engine_path = (
        SERVICES_DIR / "operations" / "correlation" / "deterministic_correlation_engine.py"
    )
    trust_graph_path = SERVICES_DIR / "operations" / "correlation" / "trust_graph.py"
    admin_api_path = API_DIR / "operations_correlation_admin.py"
    portal_api_path = API_DIR / "operations_correlation_portal.py"
    risk_path = SERVICES_DIR / "operations" / "correlation" / "correlation_risk_analysis.py"
    audit_path = SERVICES_DIR / "operations" / "correlation" / "audit_events.py"
    receipts_path = SERVICES_DIR / "operations" / "correlation" / "receipts.py"

    for path in [
        engine_path,
        trust_graph_path,
        admin_api_path,
        portal_api_path,
        risk_path,
        audit_path,
        receipts_path,
    ]:
        if not validate_no_forbidden_markers(
            path, FORBIDDEN_RUNTIME_MARKERS, "Offline deterministic runtime constraints"
        ):
            success = False
        if not validate_no_forbidden_markers(path, GRAPH_DB_MARKERS, "Graph DB independence"):
            success = False

    admin_api_path = API_DIR / "operations_correlation_admin.py"
    if not validate_advisory_only(admin_api_path):
        success = False
    if not validate_advisory_only(portal_api_path):
        success = False
    if not validate_dry_run(admin_api_path):
        success = False
    if not validate_tenant_isolation():
        success = False
    if not validate_route_registration():
        success = False

    # 4. Claims Validation
    print("\n[4/5] Checking for prohibited claims...")
    docs_path = DOCS_DIR / "operations" / "operations_correlation_engine.md"
    if docs_path.exists():
        for claim in PROHIBITED_CLAIMS:
            if not check_string_in_file(docs_path, claim, must_be_present=False):
                success = False

    # 5. Receipt & Audit Check
    print("\n[5/5] Validating receipts and audit events...")
    if not check_string_in_file(receipts_path, "build_correlation_receipt"):
        success = False
    if not check_string_in_file(receipts_path, "build_trust_link_receipt"):
        success = False
    if not check_string_in_file(receipts_path, "build_graph_summary_receipt"):
        success = False
    if not check_string_in_file(audit_path, "log_correlation_created"):
        success = False
    if not check_string_in_file(audit_path, "log_trust_link_created"):
        success = False
    if not check_string_in_file(audit_path, "log_graph_generated"):
        success = False

    print("\n--------------------------------------------------")
    if success:
        print(f"Phase {PHASE} Validation: SUCCESS")
        sys.exit(0)
    else:
        print(f"Phase {PHASE} Validation: FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
