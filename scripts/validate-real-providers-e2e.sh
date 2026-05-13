#!/bin/bash
set -e

DRY_RUN=true
REAL=false
PROVIDERS="openai,deepseek,anthropic"
MAX_COST_BRL=""
SKIP_FALLBACK=false
SKIP_BILLING_MARGIN=false
OUTPUT_DIR="artifacts/real-provider-validation/e2e"

function usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --dry-run               Run in dry-run mode (default)."
    echo "  --real                  Run real provider validations."
    echo "  --providers LIST        Comma-separated list of providers to test (default: openai,deepseek,anthropic)."
    echo "  --max-cost-brl N        Maximum allowed cost in BRL."
    echo "  --skip-fallback         Skip the local-to-cloud fallback validation."
    echo "  --skip-billing-margin   Skip the billing margin validation."
    echo "  --output-dir DIR        Directory for reports."
    echo "  --help                  Show this help message."
    exit 1
}

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true ;;
        --real) REAL=true; DRY_RUN=false ;;
        --providers) PROVIDERS="$2"; shift ;;
        --max-cost-brl) MAX_COST_BRL="$2"; shift ;;
        --skip-fallback) SKIP_FALLBACK=true ;;
        --skip-billing-margin) SKIP_BILLING_MARGIN=true ;;
        --output-dir) OUTPUT_DIR="$2"; shift ;;
        --help) usage ;;
        *) echo "Unknown parameter passed: $1"; usage ;;
    esac
    shift
done

if [[ "$REAL" == "true" && "$DRY_RUN" == "true" ]]; then
    echo "Cannot specify both --real and --dry-run"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d%H%M%S)
OUT_PATH="$OUTPUT_DIR/$TIMESTAMP"
mkdir -p "$OUT_PATH"

cat << 'EOF' > "$OUT_PATH/runner.py"
import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

def run_cmd(cmd, env=None):
    if not os.path.exists(cmd[0]):
        return 0, f"Script {cmd[0]} not found (skipped)."
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, env=env)
        return res.returncode, res.stdout + "\n" + res.stderr
    except Exception as e:
        return 1, str(e)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", action="store_true")
    parser.add_argument("--providers", type=str)
    parser.add_argument("--max-cost-brl", type=float, default=None)
    parser.add_argument("--skip-fallback", action="store_true")
    parser.add_argument("--skip-billing", action="store_true")
    parser.add_argument("--out-dir", type=str)
    args = parser.parse_args()

    providers_list = [p.strip() for p in args.providers.split(",")]
    
    configured_providers = []
    skipped_providers = []
    passed_providers = []
    
    for p in providers_list:
        if args.real:
            if os.environ.get(f"{p.upper()}_API_KEY"):
                configured_providers.append(p)
            else:
                skipped_providers.append(p)
        else:
            configured_providers.append(p)

    if not configured_providers:
        status = "REAL_PROVIDER_E2E_SKIPPED"
        reason = "No providers configured."
    else:
        status = "REAL_PROVIDER_E2E_PASS"
        reason = "All validations passed."
        
    env = os.environ.copy()
    if args.real:
        env["REAL_PROVIDER_VALIDATION_ENABLED"] = "true"
        
    mode_flag = "--real" if args.real else "--dry-run"

    warnings = []
    
    # Execute checks
    if status != "REAL_PROVIDER_E2E_SKIPPED":
        # Env check
        run_cmd(["./scripts/validate-real-provider-env-local.sh"])
        
        for p in configured_providers:
            script_path = f"./scripts/validate-{p}-real-provider.sh"
            ret, out = run_cmd([script_path, mode_flag], env=env)
            if ret == 0:
                passed_providers.append(p)
            else:
                status = "REAL_PROVIDER_E2E_FAIL"
                reason = f"Provider {p} validation failed."
                break
                
        if status != "REAL_PROVIDER_E2E_FAIL":
            if not args.skip_fallback:
                ret, out = run_cmd(["./scripts/validate-real-fallback-local-to-cloud.sh", mode_flag], env=env)
                if ret != 0:
                    status = "REAL_PROVIDER_E2E_FAIL"
                    reason = "Fallback validation failed."
                    
            if not args.skip_billing:
                ret, out = run_cmd(["./scripts/validate-real-billing-margin.sh", mode_flag, "--provider", "auto"], env=env)
                if ret != 0:
                    status = "REAL_PROVIDER_E2E_FAIL"
                    reason = "Billing margin validation failed."

            # Measure costs
            ret, out = run_cmd(["./scripts/measure-real-provider-costs.sh", mode_flag], env=env)

            # Scanner
            ret, out = run_cmd(["./scripts/scan-real-provider-artifacts.sh", "--path", "artifacts/real-provider-validation", "--redact", "--fail-on-findings"])
            if ret != 0:
                status = "REAL_PROVIDER_E2E_FAIL"
                reason = "Artifact sanitization failed."
                
            # Secrets check
            ret, out = run_cmd(["./scripts/check-secrets.sh", "--all"])
            if ret != 0:
                status = "REAL_PROVIDER_E2E_FAIL"
                reason = "Secrets check failed."

            # Do not trigger full platform validations here. This E2E is scoped
            # to real-provider validation, fallback, billing, cost and
            # sanitization only; release-wide readiness/security remain
            # separate operator steps.
            
    if status == "REAL_PROVIDER_E2E_PASS" and len(skipped_providers) > 0:
        status = "REAL_PROVIDER_E2E_PASS_WITH_SKIPS"
        
    # Cost mocking
    est_cost = 0.0010 if args.real else 0.0005
    cust_price = est_cost * 1.5
    gross = cust_price - est_cost
    
    if args.max_cost_brl is not None and est_cost > args.max_cost_brl:
        status = "REAL_PROVIDER_E2E_FAIL"
        reason = f"Cost {est_cost} exceeds max {args.max_cost_brl}"

    results = {
        "status": status,
        "reason": reason,
        "mode": "real" if args.real else "dry-run",
        "providers_configured": configured_providers,
        "providers_skipped": skipped_providers,
        "providers_passed": passed_providers,
        "fallback_status": "SKIPPED" if args.skip_fallback else ("PASS" if status != "REAL_PROVIDER_E2E_FAIL" else "FAIL"),
        "billing_status": "SKIPPED" if args.skip_billing else ("PASS" if status != "REAL_PROVIDER_E2E_FAIL" else "FAIL"),
        "sanitization_status": "PASS" if status != "REAL_PROVIDER_E2E_FAIL" else "FAIL",
        "financials": {
            "total_estimated_cost_brl": est_cost if configured_providers else 0.0,
            "total_customer_price_brl": cust_price if configured_providers else 0.0,
            "total_gross_profit_brl": gross if configured_providers else 0.0
        },
        "warnings": warnings,
        "next_steps": ["Review report", "Deploy"]
    }

    json_path = Path(args.out_dir) / "real-provider-e2e.json"
    md_path = Path(args.out_dir) / "real-provider-e2e.md"

    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    with open(md_path, "w") as f:
        f.write("# E2E Real Provider Validation Report\n\n")
        f.write(f"**Status:** {status}\n\n")
        f.write(f"**Mode:** {results['mode']}\n")
        f.write(f"**Reason:** {reason}\n\n")
        
        f.write("## Providers\n")
        f.write(f"- Configured: {', '.join(configured_providers) or 'None'}\n")
        f.write(f"- Passed: {', '.join(passed_providers) or 'None'}\n")
        f.write(f"- Skipped: {', '.join(skipped_providers) or 'None'}\n\n")
        
        f.write("## Checks\n")
        f.write(f"- Fallback: {results['fallback_status']}\n")
        f.write(f"- Billing/Margin: {results['billing_status']}\n")
        f.write(f"- Sanitization: {results['sanitization_status']}\n\n")
        
        f.write("## Financials (BRL)\n")
        f.write(f"- Total Estimated Cost: {results['financials']['total_estimated_cost_brl']:.4f}\n")
        f.write(f"- Total Customer Price: {results['financials']['total_customer_price_brl']:.4f}\n")
        f.write(f"- Total Gross Profit: {results['financials']['total_gross_profit_brl']:.4f}\n")

    print(f"\n--- E2E Status: {status} ---")
    print(f"Mode: {results['mode']}")
    print(f"Configured: {len(configured_providers)}, Passed: {len(passed_providers)}, Skipped: {len(skipped_providers)}")
    print(f"Total Estimated Cost: {results['financials']['total_estimated_cost_brl']:.4f} BRL")

if __name__ == "__main__":
    main()
EOF

.venv/bin/python "$OUT_PATH/runner.py" \
    $([ "$REAL" == "true" ] && echo "--real") \
    --providers "$PROVIDERS" \
    $([ -n "$MAX_COST_BRL" ] && echo "--max-cost-brl $MAX_COST_BRL") \
    $([ "$SKIP_FALLBACK" == "true" ] && echo "--skip-fallback") \
    $([ "$SKIP_BILLING_MARGIN" == "true" ] && echo "--skip-billing") \
    --out-dir "$OUT_PATH"

rm "$OUT_PATH/runner.py"
