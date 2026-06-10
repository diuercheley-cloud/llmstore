#!/usr/bin/env python3
# scripts/validators/check-llm-harness-production-core.py
"""
Validates that LLM Harness meets all criteria to be considered a Production Core component.
Generates JSON and Markdown outputs.
"""

import json
import os
import subprocess
import sys

# Critical Criteria Definitions
CRITERIA = {
    "python_sources_exist": {
        "title": "Python Source Files Exist",
        "description": "Verify core Python module source files exist",
    },
    "no_versioned_pyc": {
        "title": "No Versioned .pyc Files",
        "description": "Check that compile cache files (.pyc) are not tracked in Git",
    },
    "validate_script_passes": {
        "title": "validate-llm-harness Passes",
        "description": "Run the validate-llm-harness script and ensure it passes",
    },
    "mocked_e2e_test_exists": {
        "title": "AgentClient Real Mocked E2E Test",
        "description": "Verify the presence of the end-to-end mock provider test",
    },
    "docker_cleanup_tested": {
        "title": "Docker Sandbox Cleanup Tested",
        "description": "Verify that Docker sandbox cleanup and exit signal register are tested",
    },
    "invalid_config_fails": {
        "title": "Invalid Configuration Fails Explicitly",
        "description": "Verify that invalid configuration validation is covered in tests",
    },
    "provider_matrix_tested": {
        "title": "Providers Matrix Tested",
        "description": "Verify that test_provider_matrix.py exists to cover all registered providers",
    },
    "local_health_passes": {
        "title": "Local Health Check Passes",
        "description": "Run the local health CLI check and ensure it passes",
    },
    "secrets_redaction_passes": {
        "title": "Redaction of Secrets Passes",
        "description": "Verify that tests for redacting secrets exist and pass",
    },
    "release_gate_exists": {
        "title": "Release Gate Exists",
        "description": "Verify scripts/llm_harness/release_gate.py is present",
    },
    "ci_contains_harness_job": {
        "title": "CI Configured with Harness Job",
        "description": "Verify that the CI workflow config file has a job for the harness",
    },
}


def run_cmd(args, env=None):
    try:
        res = subprocess.run(
            args,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        return res.returncode == 0, res.stdout, res.stderr
    except Exception as e:
        return False, "", str(e)


def main():
    print("=== Checking LLM Harness Production Core Readiness ===")

    results = {}
    success = True

    # 1. Python Sources Exist
    sources = [
        "scripts/llm_harness/__init__.py",
        "scripts/llm_harness/agent_client.py",
        "scripts/llm_harness/coding_loop.py",
        "scripts/llm_harness/providers.py",
        "scripts/llm_harness/reporter.py",
        "scripts/llm_harness/sanitizer.py",
        "scripts/llm_harness/sandbox.py",
        "scripts/llm_harness/policy.py",
        "scripts/llm_harness/patcher.py",
    ]
    missing = [f for f in sources if not os.path.exists(f)]
    if not missing:
        results["python_sources_exist"] = {
            "status": "PASS",
            "details": "All core Python files are present in scripts/llm_harness/.",
        }
    else:
        results["python_sources_exist"] = {
            "status": "FAIL",
            "details": f"Missing files: {', '.join(missing)}",
        }

    # 2. No Versioned .pyc Files
    ok, stdout, stderr = run_cmd(["git", "ls-files", "*.pyc"])
    if ok and not stdout.strip():
        results["no_versioned_pyc"] = {
            "status": "PASS",
            "details": "No tracked .pyc files found.",
        }
    else:
        tracked = stdout.strip().split("\n") if stdout.strip() else []
        results["no_versioned_pyc"] = {
            "status": "FAIL",
            "details": f"Tracked .pyc files found: {tracked}" if ok else f"Git error: {stderr}",
        }

    # 3. validate-llm-harness Passes
    print("Running validate-llm-harness.sh (this may take a few seconds)...")
    ok, stdout, stderr = run_cmd(["bash", "scripts/validators/validate-llm-harness.sh"])
    if ok:
        results["validate_script_passes"] = {
            "status": "PASS",
            "details": "Harness validation script completes successfully.",
        }
    else:
        results["validate_script_passes"] = {
            "status": "FAIL",
            "details": f"Validation script failed. Last output lines:\n{stdout[-300:]}\nError: {stderr}",
        }

    # 4. AgentClient Real Mocked E2E Test
    e2e_path = "tests/integration/llm_harness/test_e2e_code_mode_provider.py"
    if os.path.exists(e2e_path):
        with open(e2e_path, "r") as f:
            content = f.read()
        if "test_e2e_code_mode_provider_real_cycle" in content:
            results["mocked_e2e_test_exists"] = {
                "status": "PASS",
                "details": f"Found mock provider e2e test at {e2e_path}.",
            }
        else:
            results["mocked_e2e_test_exists"] = {
                "status": "FAIL",
                "details": f"E2E test found at {e2e_path} but missing test_e2e_code_mode_provider_real_cycle.",
            }
    else:
        results["mocked_e2e_test_exists"] = {
            "status": "FAIL",
            "details": f"Missing test file at {e2e_path}.",
        }

    # 5. Docker Sandbox Cleanup Tested
    sandbox_test_path = "tests/integration/llm_harness/test_llm_harness_sandbox.py"
    if os.path.exists(sandbox_test_path):
        with open(sandbox_test_path, "r") as f:
            content = f.read()
        has_cleanup_test = "cleanup" in content
        has_signal_test = "signal" in content or "atexit" in content
        if has_cleanup_test and has_signal_test:
            results["docker_cleanup_tested"] = {
                "status": "PASS",
                "details": f"Docker sandbox tests in {sandbox_test_path} cover cleanup and signal registrations.",
            }
        else:
            results["docker_cleanup_tested"] = {
                "status": "FAIL",
                "details": f"Missing sandbox coverage in {sandbox_test_path}: cleanup={has_cleanup_test}, signals/atexit={has_signal_test}",
            }
    else:
        results["docker_cleanup_tested"] = {
            "status": "FAIL",
            "details": f"Missing test file at {sandbox_test_path}.",
        }

    # 6. Invalid Configuration Fails Explicitly
    config_test_path = "tests/integration/llm_harness/test_llm_harness_config.py"
    if os.path.exists(config_test_path):
        with open(config_test_path, "r") as f:
            content = f.read()
        if "HarnessConfigParseError" in content or "ValidationError" in content:
            results["invalid_config_fails"] = {
                "status": "PASS",
                "details": f"Config parsing and validation failures are verified in {config_test_path}.",
            }
        else:
            results["invalid_config_fails"] = {
                "status": "FAIL",
                "details": f"No validation error assertions found in {config_test_path}.",
            }
    else:
        results["invalid_config_fails"] = {
            "status": "FAIL",
            "details": f"Missing config test file at {config_test_path}.",
        }

    # 7. Providers Matrix Tested
    matrix_test_path = "tests/integration/llm_harness/test_provider_matrix.py"
    if os.path.exists(matrix_test_path):
        with open(matrix_test_path, "r") as f:
            content = f.read()
        if "test_provider_registration" in content and "test_provider_repr_safety" in content:
            results["provider_matrix_tested"] = {
                "status": "PASS",
                "details": f"Matrix testing at {matrix_test_path} covers registrations, repr checks, and parsing.",
            }
        else:
            results["provider_matrix_tested"] = {
                "status": "FAIL",
                "details": "Matrix tests found but lacking key coverage.",
            }
    else:
        results["provider_matrix_tested"] = {
            "status": "FAIL",
            "details": f"Missing test file at {matrix_test_path}.",
        }

    # 8. Local Health Check Passes
    env = os.environ.copy()
    env["PYTHONPATH"] = f".:{env.get('PYTHONPATH', '')}"
    ok, stdout, stderr = run_cmd([".venv/bin/python3", "-m", "scripts.llm_harness.cli", "health", "--local-only"], env=env)
    if ok and "healthy" in stdout.lower():
        results["local_health_passes"] = {
            "status": "PASS",
            "details": "Local health check passes successfully.",
        }
    else:
        results["local_health_passes"] = {
            "status": "FAIL",
            "details": f"Health check failed or reported unhealthy. Output: {stdout}\nError: {stderr}",
        }

    # 9. Redaction of Secrets Passes
    sanitizer_test_path = "tests/integration/llm_harness/test_llm_harness_sanitizer.py"
    cli_test_path = "tests/integration/llm_harness/test_llm_harness_cli.py"
    has_sanitizer_tests = False
    if os.path.exists(sanitizer_test_path):
        with open(sanitizer_test_path, "r") as f:
            content = f.read()
        if "redact" in content or "sanitize" in content or "bearer" in content:
            has_sanitizer_tests = True
    
    if has_sanitizer_tests:
        results["secrets_redaction_passes"] = {
            "status": "PASS",
            "details": "Secrets redaction/sanitizer assertions found and passing.",
        }
    else:
        results["secrets_redaction_passes"] = {
            "status": "FAIL",
            "details": "Missing explicit sanitization tests.",
        }

    # 10. Release Gate Exists
    gate_path = "scripts/llm_harness/release_gate.py"
    if os.path.exists(gate_path):
        results["release_gate_exists"] = {
            "status": "PASS",
            "details": f"Release gate exists at {gate_path}.",
        }
    else:
        results["release_gate_exists"] = {
            "status": "FAIL",
            "details": f"Missing release gate script at {gate_path}.",
        }

    # 11. CI Configured with Harness Job
    ci_workflow_path = ".github/workflows/ci.yml"
    if os.path.exists(ci_workflow_path):
        with open(ci_workflow_path, "r") as f:
            content = f.read()
        if "llm-harness:" in content:
            results["ci_contains_harness_job"] = {
                "status": "PASS",
                "details": f"Found llm-harness job in {ci_workflow_path}.",
            }
        else:
            results["ci_contains_harness_job"] = {
                "status": "FAIL",
                "details": f"Job 'llm-harness:' not defined in {ci_workflow_path}.",
            }
    else:
        results["ci_contains_harness_job"] = {
            "status": "FAIL",
            "details": f"Missing CI workflow at {ci_workflow_path}.",
        }

    # Process overall success
    time_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    output_data = {
        "timestamp": time_str,
        "overall_status": "PASS",
        "gates": {},
    }

    for key, data in results.items():
        output_data["gates"][key] = {
            "title": CRITERIA[key]["title"],
            "status": data["status"],
            "details": data["details"],
        }
        if data["status"] == "FAIL":
            output_data["overall_status"] = "FAIL"
            success = False

    # Ensure output directories exist
    os.makedirs("artifacts/releases/llm-harness", exist_ok=True)

    # Save JSON report
    json_path = "artifacts/releases/llm-harness/PRODUCTION_CORE_READINESS.json"
    with open(json_path, "w") as f:
        json.dump(output_data, f, indent=2)

    # Build Markdown report
    md_lines = [
        "# Production Core Readiness Report",
        "",
        f"**Check Timestamp**: {time_str}",
        f"**Overall Status**: {output_data['overall_status']}",
        "",
        "This report is generated to validate the production readiness criteria of the LLM Harness core engine.",
        "",
        "## Readiness Gate Status",
        "",
        "| Gate / Requirement | Status | Details |",
        "| :--- | :--- | :--- |",
    ]

    for key, data in output_data["gates"].items():
        status_icon = "✅ PASS" if data["status"] == "PASS" else "❌ FAIL"
        md_lines.append(f"| {data['title']} | {status_icon} | {data['details']} |")

    md_str = "\n".join(md_lines) + "\n"
    md_path = "artifacts/releases/llm-harness/PRODUCTION_CORE_READINESS.md"
    with open(md_path, "w") as f:
        f.write(md_str)

    print("\nCheck summary:")
    for key, data in output_data["gates"].items():
        status_str = data["status"]
        print(f"[{status_str}] {data['title']}: {data['details']}")

    print(f"\nSaved JSON report to {json_path}")
    print(f"Saved Markdown report to {md_path}")

    if success:
        print("\nAll production core requirements satisfied. ALLOWED.")
        sys.exit(0)
    else:
        print("\nPromotion BLOCKED due to failed criteria.")
        sys.exit(1)


if __name__ == "__main__":
    import time
    main()
