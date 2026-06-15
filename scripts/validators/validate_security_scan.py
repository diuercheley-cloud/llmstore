#!/usr/bin/env python3
import json
import os
import subprocess
import sys


def main():
    print("==> Running Bandit Security Scan...")
    os.makedirs("artifacts/reports", exist_ok=True)
    
    # Determine python/venv executable path
    python_bin = sys.executable
    venv_dir = os.path.dirname(python_bin)
    
    def find_tool(name):
        # 1. Try same dir as python
        path = os.path.join(venv_dir, name)
        if os.path.exists(path):
            return path
        # 2. Try .venv/bin
        path = os.path.join(os.getcwd(), ".venv", "bin", name)
        if os.path.exists(path):
            return path
        # 3. Try system path
        return name

    bandit_path = find_tool("bandit")
    semgrep_path = find_tool("semgrep")
    
    # Run Bandit
    bandit_cmd = [
        bandit_path,
        "-c", "bandit.yaml",
        "-r", ".",
        "-b", "config/bandit-baseline.json",
        "-f", "json",
        "-o", "artifacts/reports/bandit-results.json"
    ]
    
    print(f"Running command: {' '.join(bandit_cmd)}")
    bandit_res = subprocess.run(bandit_cmd, capture_output=True, text=True)
    
    bandit_failed = False
    # Bandit returns 1 if issues found, but we check the json
    try:
        if os.path.exists("artifacts/reports/bandit-results.json"):
            with open("artifacts/reports/bandit-results.json") as f:
                bandit_data = json.load(f)
            new_issues = bandit_data.get("results", [])
            # Filter for HIGH/MEDIUM severity
            critical_new_issues = [
                i for i in new_issues 
                if i.get("issue_severity") in ("HIGH", "MEDIUM")
            ]
            if critical_new_issues:
                print(f"FAILED: Bandit found {len(critical_new_issues)} new HIGH/MEDIUM severity issues:")
                for issue in critical_new_issues:
                    print(f"  - [{issue.get('issue_severity')}] {issue.get('issue_text')} at {issue.get('filename')}:{issue.get('line_number')}")
                bandit_failed = True
            else:
                print("Bandit: No new HIGH/MEDIUM severity issues found.")
        else:
            print("Bandit failed to generate report.")
            bandit_failed = True
    except Exception as e:
        print(f"Error parsing bandit results: {e}")
        bandit_failed = True

    print("\n==> Running Semgrep Security Scan...")
    
    semgrep_cmd = [
        semgrep_path,
        "scan",
        "--config", "auto",
    ]
    
    if os.path.exists(".semgrep.yml"):
        semgrep_cmd.extend(["--config", ".semgrep.yml"])

        
    semgrep_cmd.extend([
        "--json",
        "--output", "artifacts/reports/semgrep-results.json"
    ])
    
    print(f"Running command: {' '.join(semgrep_cmd)}")
    subprocess.run(semgrep_cmd, capture_output=True, text=True)


    
    semgrep_failed = False
    try:
        with open("artifacts/reports/semgrep-results.json") as f:
            semgrep_data = json.load(f)
        semgrep_findings = semgrep_data.get("results", [])
        
        # Load baseline
        with open("config/semgrep-baseline.json") as f:
            baseline_data = json.load(f)
        baseline_keys = {(b["check_id"], b["path"]) for b in baseline_data}
        
        new_semgrep_findings = []
        for finding in semgrep_findings:
            key = (finding["check_id"], finding["path"])
            if key not in baseline_keys:
                new_semgrep_findings.append(finding)
                
        if new_semgrep_findings:
            print(f"FAILED: Semgrep found {len(new_semgrep_findings)} new security issues:")
            for finding in new_semgrep_findings:
                sev = finding.get("extra", {}).get("severity", "UNKNOWN")
                msg = finding.get("extra", {}).get("message", "")
                line = finding.get("start", {}).get("line", 0)
                print(f"  - [{sev}] {msg} at {finding.get('path')}:{line}")
            semgrep_failed = True
        else:
            print("Semgrep: No new issues found.")
    except Exception as e:
        print(f"Error checking semgrep results: {e}")
        semgrep_failed = True

    if bandit_failed or semgrep_failed:
        sys.exit(1)
    else:
        print("\nAll security checks passed (matched against baselines).")
        sys.exit(0)

if __name__ == "__main__":
    main()
