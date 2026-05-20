import os
import sys
import yaml

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

def extract_purpose_and_confirm(filepath):
    purpose = "Operational script for stack management."
    has_confirm_pattern = False
    
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
        # Parse purpose from comments
        comments = []
        for line in lines[:15]:
            stripped = line.strip()
            if stripped.startswith("#!"):
                continue
            if stripped.startswith("#"):
                comment_text = stripped.lstrip("#").strip()
                if comment_text and not comment_text.startswith("!"):
                    comments.append(comment_text)
            elif '"""' in stripped or "'''" in stripped:
                continue
            elif comments:
                break
                
        if comments:
            purpose = " ".join(comments[:3])
            
        content = "".join(lines).lower()
        confirm_keywords = ["read -p", "confirm", "prompt", "are you sure", "read -r", "select ", "stdin.read", "input(", "click.confirm"]
        if any(kw in content for kw in confirm_keywords):
            has_confirm_pattern = True
            
    except Exception:
        pass
        
    return purpose, has_confirm_pattern

def generate():
    manifest_path = os.path.join(base_dir, "scripts/manifest.yaml")
    records = []
    
    scripts_dir = os.path.join(base_dir, "scripts")
    for root, dirs, files in os.walk(scripts_dir):
        if "__pycache__" in root:
            continue
            
        for file in files:
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, base_dir)
            
            # Check if file is executable
            if not os.access(filepath, os.X_OK):
                continue
                
            purpose, has_confirm = extract_purpose_and_confirm(filepath)
            
            # Default properties
            owner = "platform-ops"
            status = "internal"
            category = "operations"
            
            name_lower = file.lower()
            if name_lower.startswith("validate"):
                category = "validation"
            elif name_lower.startswith("test"):
                category = "testing"
            elif name_lower.startswith("generate") or name_lower.startswith("report"):
                category = "reports"
            elif name_lower.startswith("check"):
                category = "compliance"

            # Status based on name
            if "legacy" in name_lower or "deprecated" in name_lower or "old" in name_lower:
                status = "deprecated"
            elif "experimental" in name_lower or "demo" in name_lower or "prototype" in name_lower:
                status = "experimental"
                
            readme_scripts = [
                "scripts/up.sh",
                "scripts/down.sh",
                "scripts/check-secrets.sh",
                "scripts/generate-enterprise-pack.sh",
                "scripts/generate-customer-readiness-report.sh",
                "scripts/generate-acceptance-report.sh"
            ]
            if rel_path in readme_scripts:
                status = "supported"
                
            requires_docker = False
            requires_network = False
            requires_gpu = False
            writes_files = False
            is_destructive = False
            outputs = []

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                content_lower = content.lower()
                
                if "docker" in content_lower or "docker-compose" in content_lower:
                    requires_docker = True
                
                # Broad network keyword matching
                network_keywords = ["curl", "wget", "git clone", "git fetch", "ping", "pip install", "npm install", "requests.", "httpx.", "urllib"]
                if any(kw in content_lower for kw in network_keywords):
                    requires_network = True
                    
                if any(kw in content_lower for kw in ["nvidia-smi", "cuda", "gpu"]):
                    requires_gpu = True
                    
                if any(kw in content_lower for kw in ["> ", ">> ", "tee ", "mkdir ", "write_to_file", "open("]):
                    writes_files = True
                    outputs = ["artifacts/*"] if category == "reports" else ["logs/*"]
                
                # Destructive is only true for database drop, demo reset, or client purge operations affecting persistence
                if any(kw in name_lower for kw in ["reset-demo", "purge-data", "drop-db", "destroy-platform"]):
                    is_destructive = True
                elif category not in ["validation", "testing"] and any(kw in content_lower for kw in ["drop database", "dropdb", "delete from clients", "truncate table"]):
                    is_destructive = True
                    
            except Exception:
                pass

            docs_url = None
            if status == "supported":
                docs_url = "/docs/operations/script-governance.md"

            records.append({
                "path": rel_path,
                "purpose": purpose,
                "owner": owner,
                "category": category,
                "status": status,
                "safe_to_run_local": not (requires_gpu or requires_docker or is_destructive),
                "requires_docker": requires_docker,
                "requires_network": requires_network,
                "requires_gpu": requires_gpu,
                "writes_files": writes_files,
                "outputs": outputs if writes_files else [],
                "is_destructive": is_destructive,
                "docs_url": docs_url
            })

    records.sort(key=lambda r: r["path"])

    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(records, f, sort_keys=False, allow_unicode=True)

    print(f"Generated {len(records)} entries in scripts/manifest.yaml")

if __name__ == "__main__":
    generate()
