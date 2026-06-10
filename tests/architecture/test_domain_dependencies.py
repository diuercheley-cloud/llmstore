import ast
import os
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2] / "control_plane/app"

# Rule Definitions
# (source_dir, allowed_deps, forbidden_deps)
RULES = {
    "api": ({"services", "schemas", "core"}, set()),
    "services": ({"core", "schemas", "models"}, {"api"}),
    "models": ({"core"}, {"services", "api"}),
}

def get_imports(file_path: Path):
    with open(file_path, "r") as f:
        tree = ast.parse(f.read())
    
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.add(n.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])
    return imports

def test_domain_dependencies():
    violations = []
    
    for root, dirs, files in os.walk(ROOT):
        parts = Path(root).relative_to(ROOT).parts
        if not parts: continue
        domain = parts[0]
        
        if domain not in RULES: continue
        
        allowed, forbidden = RULES[domain]
        
        for file in files:
            if not file.endswith(".py"): continue
            file_path = Path(root) / file
            imports = get_imports(file_path)
            
            # Check forbidden
            for imp in imports:
                if imp in forbidden:
                    violations.append(f"{file_path} imports forbidden module '{imp}'")
                    
    assert not violations, "\n".join(violations)
