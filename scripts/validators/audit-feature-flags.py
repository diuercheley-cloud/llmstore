#!/usr/bin/env python3
import os
import sys

import yaml

FEATURE_FLAGS_YAML = "config/feature-flags.yaml"
ENV_EXAMPLE = ".env.example"
CODE_DIRS = ["control_plane/app", "frontend/src", "scripts", "docs"]

def load_flags():
    with open(FEATURE_FLAGS_YAML, "r") as f:
        return yaml.safe_load(f)

def check_usage(flag_name):
    # Search for the flag name in the codebase
    attr_name = flag_name.lower()
    
    # We want to find cases where it's used as:
    # 1. AGENT_FLAG_NAME (env var or string)
    # 2. settings.agent_flag_name (attribute)
    # 3. agent_flag_name (sometimes used as local var or in dicts)
    
    try:
        # Check in app code, frontend, scripts, docs
        # Using grep -rE to match either the exact flag name or the attribute name
        pattern = f"{flag_name}|{attr_name}"
        
        count = 0
        for d in CODE_DIRS:
            if not os.path.exists(d): continue
            cmd = f"grep -rE \"{pattern}\" {d} --exclude-dir=\"__pycache__\" --exclude-dir=\".ruff_cache\" --exclude=\"*.pyc\" | grep -v \"feature-flags.yaml\" | wc -l"
            count += int(os.popen(cmd).read().strip())
        
        return count
    except Exception as e:
        print(f"Error checking {flag_name}: {e}")
        return 0

def is_in_env_example(flag_name):
    try:
        cmd = f"grep \"{flag_name}\" {ENV_EXAMPLE} | wc -l"
        return int(os.popen(cmd).read().strip()) > 0
    except:
        return False

def main():
    flags = load_flags()
    orphans = []
    issues_report = []
    
    print(f"Auditing {len(flags)} feature flags...\n")
    
    for flag in flags:
        name = flag.get("name")
        owner = flag.get("owner")
        status = flag.get("status")
        default_val = flag.get("default")
        risk = flag.get("risk_level")
        
        usage_count = check_usage(name)
        in_env = is_in_env_example(name)
        
        issues = []
        if not owner:
            issues.append("MISSING OWNER")
        
        if usage_count == 0:
            if status != "removed":
                issues.append("ORPHAN (Not found in code/docs)")
                orphans.append(name)
        
        if risk == "high" and default_val is True:
            issues.append("HIGH-RISK DEFAULT TRUE")
            
        if status == "deprecated":
            if not flag.get("replacement"):
                issues.append("DEPRECATED WITHOUT REPLACEMENT")
            if not flag.get("remove_after"):
                issues.append("DEPRECATED WITHOUT REMOVAL TARGET")

        if issues:
            issues_report.append({
                "name": name,
                "issues": issues,
                "status": status,
                "owner": owner,
                "usage": usage_count
            })

    print("## Feature Flag Audit Report\n")
    if not issues_report:
        print("No issues found.")
    else:
        for item in issues_report:
            print(f"### {item['name']}")
            print(f"- Status: {item['status']}")
            print(f"- Owner: {item['owner']}")
            print(f"- Usage count: {item['usage']}")
            print(f"- Issues: {', '.join(item['issues'])}")
            print()
            
    if "--json" in sys.argv:
        import json
        with open("artifacts/feature-flag-audit.json", "w") as f:
            json.dump(issues_report, f, indent=2)

if __name__ == "__main__":
    main()
