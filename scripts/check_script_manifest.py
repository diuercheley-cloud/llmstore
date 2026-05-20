import os
import sys
import re
import yaml

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def check_script_governance():
    manifest_path = os.path.join(base_dir, "scripts/manifest.yaml")
    readme_path = os.path.join(base_dir, "README.md")
    
    if not os.path.exists(manifest_path):
        print(f"FAIL: scripts/manifest.yaml not found at {manifest_path}")
        sys.exit(1)
        
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
    except Exception as e:
        print(f"FAIL: Error reading scripts/manifest.yaml: {e}")
        sys.exit(1)

    # Build manifest mapping
    manifest = {entry["path"]: entry for entry in data}
    
    # 1. Gather all executable files in scripts/ (ignoring __pycache__ and lib folders)
    scripts_dir = os.path.join(base_dir, "scripts")
    executables = []
    for root, dirs, files in os.walk(scripts_dir):
        if "__pycache__" in root:
            continue
        for file in files:
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, base_dir)
            if os.access(filepath, os.X_OK):
                executables.append(rel_path)

    failures = []
    
    # Check completeness
    for path in executables:
        if path not in manifest:
            failures.append(f"Script '{path}' is executable but missing from scripts/manifest.yaml.")

    # Parse README for script references
    readme_scripts = []
    if os.path.exists(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_content = f.read()
            # Look for scripts/... paths in README
            matches = re.findall(r"scripts/[a-zA-Z0-9_.-]+", readme_content)
            readme_scripts = list(set(matches))
        except Exception as e:
            print(f"WARNING: Error reading README.md: {e}")

    # Validate each manifest entry
    for path, entry in manifest.items():
        # Check if file actually exists
        full_path = os.path.join(base_dir, path)
        if not os.path.exists(full_path):
            # If a script was deleted, it shouldn't fail but warn or we can fail. Let's warn.
            print(f"WARNING: Registered script '{path}' does not exist on disk.")
            continue
            
        status = entry.get("status")
        owner = entry.get("owner")
        category = entry.get("category")
        docs_url = entry.get("docs_url")
        requires_network = entry.get("requires_network", False)
        writes_files = entry.get("writes_files", False)
        outputs = entry.get("outputs", [])
        is_destructive = entry.get("is_destructive", False)
        
        # Rule 1: No supported script without owner
        if status == "supported" and not owner:
            failures.append(f"Supported script '{path}' must have an owner.")
            
        # Rule 2: Supported script must have docs
        if status == "supported" and not docs_url:
            failures.append(f"Supported script '{path}' must have a docs_url.")
            
        # Inspect code content
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
            code_lower = code.lower()
        except Exception as e:
            print(f"WARNING: Could not read script '{path}' content: {e}")
            code = ""
            code_lower = ""

        # Rule 3: Destructive scripts must have confirmation (unless category is testing/validation)
        if is_destructive and category not in ["validation", "testing"]:
            confirm_keywords = ["read -p", "confirm", "prompt", "are you sure", "read -r", "select ", "stdin.read", "input(", "click.confirm"]
            if not any(kw in code_lower for kw in confirm_keywords):
                failures.append(f"Destructive script '{path}' must require confirmation (e.g. using read/confirm prompt in code).")

        # Rule 4: Script writing files must declare outputs
        # Scan code for write patterns
        has_write_pattern = any(kw in code_lower for kw in ["> ", ">> ", "tee ", "mkdir ", "write_to_file", "open("])
        if has_write_pattern and not writes_files:
            failures.append(f"Script '{path}' writes files but 'writes_files' is false in manifest.")
        if writes_files and not outputs:
            failures.append(f"Script '{path}' has 'writes_files' as true but 'outputs' list is empty.")

        # Rule 5: Script using network must declare it
        has_network_pattern = any(kw in code_lower for kw in ["curl", "wget", "git clone", "git fetch", "ping", "pip install", "npm install", "requests.", "httpx."])
        if has_network_pattern and not requires_network:
            failures.append(f"Script '{path}' uses network but 'requires_network' is false in manifest.")

        # Rule 6: Experimental scripts cannot appear as main paths in README
        if status == "experimental":
            # Match paths in readme
            for r_script in readme_scripts:
                # If script matches or path starts with it
                if r_script == path or r_script.startswith(path):
                    failures.append(f"Experimental script '{path}' is referenced as a main path in README.md.")

    # Generate Reports under artifacts/scripts/latest/
    reports_dir = os.path.join(base_dir, "artifacts/scripts/latest")
    os.makedirs(reports_dir, exist_ok=True)
    
    # 1. script-inventory.md
    inventory_path = os.path.join(reports_dir, "script-inventory.md")
    with open(inventory_path, "w", encoding="utf-8") as f:
        f.write("# Operational Scripts Inventory\n\n")
        f.write("Inventory of all operational scripts classified by category.\n\n")
        
        categories = sorted(list(set(e.get("category", "operations") for e in data)))
        for cat in categories:
            f.write(f"## Category: {cat.capitalize()}\n\n")
            f.write("| Path | Purpose | Owner | Status | Safe Local | writes_files | requires_network |\n")
            f.write("| --- | --- | --- | --- | --- | --- | --- |\n")
            
            cat_entries = [e for e in data if e.get("category") == cat]
            for entry in sorted(cat_entries, key=lambda e: e["path"]):
                p = entry["path"]
                purp = entry.get("purpose", "N/A").replace("\n", " ")
                o = entry.get("owner", "N/A")
                st = entry.get("status", "internal")
                safe = "✅" if entry.get("safe_to_run_local") else "❌"
                writes = "Yes" if entry.get("writes_files") else "No"
                net = "Yes" if entry.get("requires_network") else "No"
                f.write(f"| `{p}` | {purp} | `{o}` | `{st}` | {safe} | {writes} | {net} |\n")
            f.write("\n")
            
    # 2. deprecated-scripts.md
    deprecated_path = os.path.join(reports_dir, "deprecated-scripts.md")
    with open(deprecated_path, "w", encoding="utf-8") as f:
        f.write("# Deprecated Operational Scripts\n\n")
        f.write("The following scripts are deprecated and scheduled for future removal.\n\n")
        f.write("| Path | Purpose | Owner | Category | Replacement / Notes |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        
        dep_entries = [e for e in data if e.get("status") == "deprecated"]
        for entry in sorted(dep_entries, key=lambda e: e["path"]):
            p = entry["path"]
            purp = entry.get("purpose", "N/A").replace("\n", " ")
            o = entry.get("owner", "N/A")
            cat = entry.get("category", "N/A")
            f.write(f"| `{p}` | {purp} | `{o}` | `{cat}` | Replaced by new platform-freeze compliant pipelines |\n")
            
    # 3. undocumented-scripts.md
    undocumented_path = os.path.join(reports_dir, "undocumented-scripts.md")
    with open(undocumented_path, "w", encoding="utf-8") as f:
        f.write("# Undocumented Operational Scripts\n\n")
        f.write("Scripts missing formal documentation links or custom owners.\n\n")
        f.write("| Path | Category | Status | Owner | Documentation Status |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        
        undoc_entries = [e for e in data if not e.get("docs_url")]
        for entry in sorted(undoc_entries, key=lambda e: e["path"]):
            p = entry["path"]
            cat = entry.get("category", "N/A")
            st = entry.get("status", "internal")
            o = entry.get("owner", "N/A")
            f.write(f"| `{p}` | `{cat}` | `{st}` | `{o}` | Missing docs_url link |\n")

    if failures:
        print("--- Script Governance Validation Failed ---")
        for f in failures:
            print(f" - {f}")
        print(f"Total failures: {len(failures)}")
        sys.exit(1)
    else:
        print("PASS: Operational scripts governance audit passed successfully.")
        sys.exit(0)

if __name__ == "__main__":
    check_script_governance()
