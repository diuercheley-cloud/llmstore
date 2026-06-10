#!/bin/bash
# scripts/dev/run-real-provider-validation.sh

set -e

echo "Starting Real Provider Validation Suite..."

export AGENT_REAL_PROVIDER_VALIDATION_ENABLED=true
export PYTHONPATH="${PYTHONPATH}:$(pwd)/control_plane"

# Create artifacts directory if it doesn't exist
mkdir -p artifacts/evals

# Run the python script to execute validations and generate the report
cat << 'EOF' > /tmp/run_validations.py
from app.services.agents.provider_validation import RealProviderValidator, generate_markdown_report

print("Initializing Real Provider Validator...")
validator = RealProviderValidator()

print(f"Validation Enabled: {validator.is_enabled}")
print("Executing test suite against real providers (Mock/SaaS Mode)...")

report = validator.execute_suite()

report_path = "artifacts/evals/real-provider-validation.md"
generate_markdown_report(report, filepath=report_path)

print(f"Validation complete. Report generated at {report_path}")
EOF

.venv/bin/python3 /tmp/run_validations.py

echo "Running pytest for provider validations..."
.venv/bin/pytest tests/integration/evals/real_provider/test_provider_validation.py -v

echo "Real Provider Validation Suite finished successfully."
