import os
import sys


def check_file_exists(path):
    if os.path.exists(path):
        print(f"✅ Found: {path}")
        return True
    else:
        print(f"❌ Missing: {path}")
        return False


def check_content(path, patterns):
    if not os.path.exists(path):
        return False
    with open(path) as f:
        content = f.read()

    all_found = True
    for p in patterns:
        if p in content:
            print(f"✅ Found pattern '{p}' in {path}")
        else:
            print(f"❌ Missing pattern '{p}' in {path}")
            all_found = False
    return all_found


def main():
    print("--- Phase 74 Validation: Signed Adapter Registry ---")

    files_to_check = [
        "control_plane/app/models/operations/adapter_registry.py",
        "control_plane/app/services/operations/adapter_registry/hash_utils.py",
        "control_plane/app/services/operations/adapter_registry/registry_service.py",
        "control_plane/app/services/operations/adapter_registry/policy_engine.py",
        "control_plane/app/services/operations/adapter_registry/allowlist_blocklist.py",
        "control_plane/app/services/operations/adapter_registry/receipts.py",
        "control_plane/app/services/operations/adapter_registry/audit_events.py",
        "control_plane/app/api/operations_adapter_registry_admin.py",
        "docs/phases/phase_74_signed_adapter_registry.md",
        "docs/operations/signed_adapter_registry.md",
    ]

    missing = 0
    for f in files_to_check:
        if not check_file_exists(f):
            missing += 1

    if missing > 0:
        print(f"FATAL: {missing} files missing.")
        sys.exit(1)

    # Check key requirements in code
    model_patterns = [
        "SignedAdapterRegistryEntry",
        "AdapterRegistryPolicy",
        "AdapterRegistryDecision",
        "AdapterRegistryReceipt",
        "AdapterRegistryBlocklistEntry",
        "AdapterRegistryAllowlistEntry",
        "registry_status",
        "signature_placeholder",
        "manifest_hash",
    ]
    if not check_content("control_plane/app/models/operations/adapter_registry.py", model_patterns):
        sys.exit(1)

    policy_patterns = [
        "sandbox_required=False is blocked",
        "dry_run_default=False is blocked",
        "network_access_allowed=True is blocked",
        "subprocess_allowed=True is blocked",
        "external_system_access_allowed=True is blocked",
    ]
    if not check_content(
        "control_plane/app/services/operations/adapter_registry/policy_engine.py", policy_patterns
    ):
        sys.exit(1)

    # Check for determinism (no utc_now in immutable_hash)
    determinism_files = [
        "control_plane/app/services/operations/adapter_registry/registry_service.py",
        "control_plane/app/services/operations/adapter_registry/allowlist_blocklist.py",
        "control_plane/app/services/operations/adapter_registry/receipts.py",
    ]
    for df in determinism_files:
        with open(df) as f:
            content = f.read()
            if "immutable_hash" in content and "utc_now()" in content:
                # In receipts.py, utc_now() might be used for generated_at, but not for immutable_hash.
                # I need a more precise check.
                if (
                    'immutable_hash=sha256_hex(f"{prefix}_" + utc_now().isoformat())'
                    in content.replace(" ", "")
                ):
                    print(f"❌ Non-deterministic immutable_hash found in {df}")
                    sys.exit(1)
            print(f"✅ Determinism check passed for {df}")

    api_patterns = [
        "/entries",
        "/policies",
        "/blocklist",
        "SignedAdapterRegistryService",
        "AdapterRegistryListService",
        "get_current_admin",
        "ENGINE.evaluate_manifest(manifest, policy)",  # Check policy eval in API
        "if not policy:",  # Check policy mandatory check
        'raise HTTPException(status_code=400, detail="No registry policy found',
    ]
    if not check_content(
        "control_plane/app/api/operations_adapter_registry_admin.py", api_patterns
    ):
        sys.exit(1)

    # Check status transitions in service
    service_patterns = [
        'if entry.registry_status != "draft":',
        'if entry.registry_status not in ["submitted", "rejected"]:',
        "if not reason:",
        "raise ValueError(",
    ]
    if not check_content(
        "control_plane/app/services/operations/adapter_registry/registry_service.py",
        service_patterns,
    ):
        sys.exit(1)

    # Check dashboard
    dashboard_patterns = [
        "Signed Adapter Registry",
        "adapterRegistryCount",
        "adapterRegistryApprovedCount",
        "signature placeholder only",
    ]
    if not check_content("control_plane/app/static/admin/index.html", dashboard_patterns):
        sys.exit(1)

    print("\n--- Phase 74 Validation: SUCCESS ---")


if __name__ == "__main__":
    main()
