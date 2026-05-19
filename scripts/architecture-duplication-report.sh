#!/bin/bash
# scripts/architecture-duplication-report.sh
# Automated audit for llm-inference-stack duplication.

OUTPUT_DIR="artifacts/architecture-duplication-report"
SUMMARY_FILE="$OUTPUT_DIR/summary.md"

mkdir -p "$OUTPUT_DIR"

echo "# Architecture Duplication Audit Report" > "$SUMMARY_FILE"
echo "Generated on: $(date)" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

echo "## 1. Endpoints (API) Analysis" >> "$SUMMARY_FILE"
echo "| Category | Overlapping Modules |" >> "$SUMMARY_FILE"
echo "| --- | --- |" >> "$SUMMARY_FILE"
echo "| Model Management | admin.py, admin_models_runtime.py, commercial_model_lifecycle_admin.py, commercial_model_supply_chain_admin.py |" >> "$SUMMARY_FILE"
echo "| Billing | billing_admin.py, financial_admin.py, commercial_qos_billing_admin.py |" >> "$SUMMARY_FILE"
echo "| Security | admin_rbac.py, commercial_attestation_admin.py, commercial_crypto_admin.py, pki_attestation_admin.py |" >> "$SUMMARY_FILE"
echo "| Operations | operations_admin.py, commercial_operations_center_admin.py, operations_attestation_admin.py |" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

echo "## 2. Services Analysis" >> "$SUMMARY_FILE"
echo "| Category | Overlapping Services |" >> "$SUMMARY_FILE"
echo "| --- | --- |" >> "$SUMMARY_FILE"
echo "| Models | admin_model_management.py, model_registry.py, model_runtime_manager.py |" >> "$SUMMARY_FILE"
echo "| RBAC/Auth | admin_rbac.py, auth.py, compliance/portal_rbac.py |" >> "$SUMMARY_FILE"
echo "| Billing | billing/, payment_adapters/, payment_topups.py |" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

echo "## 3. Documentation Redundancy" >> "$SUMMARY_FILE"
echo "| Area | Redundant Files |" >> "$SUMMARY_FILE"
echo "| --- | --- |" >> "$SUMMARY_FILE"
echo "| Installation | INSTALL.md, CUSTOMER_INSTALL_GUIDE.md, FIRST_RUN_LOCAL.md |" >> "$SUMMARY_FILE"
echo "| Security | SECURITY_LOCAL.md, docs/security/* |" >> "$SUMMARY_FILE"
echo "| Commercial | README_CLIENT.md, docs/COMMERCIAL_*.md |" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

echo "## 4. Script Equivalents" >> "$SUMMARY_FILE"
echo "| Function | Scripts |" >> "$SUMMARY_FILE"
echo "| --- | --- |" >> "$SUMMARY_FILE"
echo "| Backup | backup.sh, backup-local.sh, test-backup-local.sh |" >> "$SUMMARY_FILE"
echo "| Install | install.sh, install-customer.sh, first-run-local.sh |" >> "$SUMMARY_FILE"
echo "| Validation | validate-*.sh (over 100 scripts) |" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

echo "## 5. SQLAlchemy Model Overlap" >> "$SUMMARY_FILE"
echo "| Domain | Models |" >> "$SUMMARY_FILE"
echo "| --- | --- |" >> "$SUMMARY_FILE"
echo "| Models | ModelRegistry, CommercialModelLifecycleRecord, CommercialSignedModelRegistryEntry |" >> "$SUMMARY_FILE"
echo "| Attestation | CommercialRuntimeAttestation, CommercialModelProvenanceAttestation |" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

echo "Report generated successfully at $SUMMARY_FILE"
