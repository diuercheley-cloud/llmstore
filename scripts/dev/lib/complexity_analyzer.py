import ast
import hashlib
import os
import re
import sys

import yaml

# Add control_plane to python path so we can import services if needed
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(base_dir, "control_plane"))

def get_sha256(filepath):
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None

def analyze_api_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)
    except Exception as e:
        print(f"Error parsing API file {filepath}: {e}")
        return []
    
    endpoints = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                func = None
                keywords = []
                args = []
                if isinstance(decorator, ast.Call):
                    func = decorator.func
                    keywords = decorator.keywords
                    args = decorator.args
                elif isinstance(decorator, ast.Attribute):
                    func = decorator
                
                if isinstance(func, ast.Attribute):
                    # Check @router.xxx(...) or @app.xxx(...)
                    if isinstance(func.value, ast.Name) and func.value.id in ("router", "app"):
                        if func.attr in ("get", "post", "put", "delete", "patch", "options", "head", "api_route"):
                            is_deprecated = False
                            for kw in keywords:
                                if kw.arg == "deprecated":
                                    if hasattr(kw.value, "value"):
                                        if kw.value.value is True:
                                            is_deprecated = True
                                    elif isinstance(kw.value, ast.NameConstant):
                                        if kw.value.value is True:
                                            is_deprecated = True
                            
                            is_internal = "internal" in os.path.basename(filepath)
                            for kw in keywords:
                                if kw.arg == "tags":
                                    if isinstance(kw.value, ast.List):
                                        for elt in kw.value.elts:
                                            if hasattr(elt, "value") and elt.value == "internal":
                                                is_internal = True
                            
                            if args and isinstance(args[0], ast.Constant):
                                if "/internal/" in str(args[0].value):
                                    is_internal = True
                            elif args and isinstance(args[0], ast.Str):
                                if "/internal/" in args[0].s:
                                    is_internal = True
                                    
                            endpoints.append({
                                "func_name": node.name,
                                "method": func.attr.upper(),
                                "deprecated": is_deprecated,
                                "internal": is_internal,
                            })
    return endpoints

def run_analysis():
    # 1. Routers & Endpoints
    routers = []
    endpoints = []
    api_dir = os.path.join(base_dir, "control_plane/app/api")
    for file in sorted(os.listdir(api_dir)):
        if file.endswith(".py") and file not in ("__init__.py", "dependencies.py", "deps.py"):
            filepath = os.path.join(api_dir, file)
            file_endpoints = analyze_api_file(filepath)
            routers.append({
                "name": file,
                "path": filepath,
                "endpoints_count": len(file_endpoints)
            })
            for ep in file_endpoints:
                ep["router"] = file
                endpoints.append(ep)

    deprecated_endpoints = [ep for ep in endpoints if ep["deprecated"]]
    internal_endpoints = [ep for ep in endpoints if ep["internal"]]

    # 2. Services & Test Cobertura
    services = []
    services_dir = os.path.join(base_dir, "control_plane/app/services")
    
    # Read test references (all test files contents concatenated for quick lookup)
    tests_content = ""
    tests_dir = os.path.join(base_dir, "tests/control_plane")
    test_files = []
    for root, dirs, files in os.walk(tests_dir):
        for file in files:
            if file.endswith(".py") and file.startswith("test_"):
                test_files.append(file)
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        tests_content += f.read() + "\n"
                except Exception:
                    pass

    for root, dirs, files in os.walk(services_dir):
        for file in sorted(files):
            if file.endswith(".py") and file != "__init__":
                service_path = os.path.join(root, file)
                rel_path = os.path.relpath(service_path, base_dir)
                basename = os.path.splitext(file)[0]
                
                # Check test file by name or content reference
                has_test_file = f"test_{file}" in test_files or f"test_{basename}.py" in test_files
                referenced_in_tests = basename in tests_content
                
                # Count classes/methods inside service
                classes_count = 0
                methods_count = 0
                try:
                    with open(service_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=service_path)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            classes_count += 1
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            methods_count += 1
                except Exception:
                    pass

                services.append({
                    "name": file,
                    "rel_path": rel_path,
                    "abs_path": service_path,
                    "classes_count": classes_count,
                    "methods_count": methods_count,
                    "has_tests": has_test_file or referenced_in_tests
                })

    services_without_tests = [s for s in services if not s["has_tests"]]

    # 3. Models
    models = []
    models_dir = os.path.join(base_dir, "control_plane/app/models")
    for root, dirs, files in os.walk(models_dir):
        for file in sorted(files):
            if file.endswith(".py") and file != "__init__.py":
                model_path = os.path.join(root, file)
                rel_path = os.path.relpath(model_path, base_dir)
                
                # Count SQLAlchemy models
                db_classes = []
                try:
                    with open(model_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=model_path)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            # Check if Base is in bases
                            for base in node.bases:
                                if isinstance(base, ast.Name) and base.id == "Base":
                                    db_classes.append(node.name)
                except Exception:
                    pass
                
                models.append({
                    "name": file,
                    "rel_path": rel_path,
                    "classes": db_classes,
                    "classes_count": len(db_classes)
                })

    # 4. Scripts
    scripts = []
    scripts_dir = os.path.join(base_dir, "scripts")
    for root, dirs, files in os.walk(scripts_dir):
        # Exclude lib and __pycache__
        if "lib" in root or "__pycache__" in root:
            continue
        for file in sorted(files):
            script_path = os.path.join(root, file)
            rel_path = os.path.relpath(script_path, base_dir)
            sha = get_sha256(script_path)
            if sha:
                scripts.append({
                    "name": file,
                    "rel_path": rel_path,
                    "sha": sha,
                    "size": os.path.getsize(script_path)
                })

    # Find duplicates
    sha_map = {}
    for s in scripts:
        sha_map.setdefault(s["sha"], []).append(s)
    
    duplicate_scripts = []
    for sha, files in sha_map.items():
        if len(files) > 1:
            duplicate_scripts.append(files)

    # 5. Feature Flags
    ff_yaml_path = os.path.join(base_dir, "config/feature-flags.yaml")
    feature_flags = []
    if os.path.exists(ff_yaml_path):
        try:
            with open(ff_yaml_path, "r", encoding="utf-8") as f:
                feature_flags = yaml.safe_load(f) or []
        except Exception as e:
            print(f"Error reading feature flags: {e}")

    # Use feature flag registry to scan for orphans
    orphans = []
    try:
        from app.services.feature_flag_registry import FeatureFlagRegistryService
        service = FeatureFlagRegistryService()
        scan_results = service.scan_orphans()
        orphans = scan_results.get("orphans", [])
    except Exception as e:
        print(f"Error scanning feature flag orphans: {e}")

    deprecated_flags = [f for f in feature_flags if f.get("status") == "deprecated"]

    # 6. Docs & Owners
    docs = []
    docs_dir = os.path.join(base_dir, "docs")
    for root, dirs, files in os.walk(docs_dir):
        for file in sorted(files):
            if file.endswith(".md"):
                doc_path = os.path.join(root, file)
                rel_path = os.path.relpath(doc_path, base_dir)
                
                # Check for owner
                owner = None
                try:
                    with open(doc_path, "r", encoding="utf-8") as f:
                        lines = [f.readline() for _ in range(30)]
                    for line in lines:
                        match = re.search(r"(?i)^\s*#*\s*(owner|autor|owner-team)\s*:\s*([^\n\r]+)", line)
                        if match:
                            owner = match.group(2).strip()
                            break
                except Exception:
                    pass
                
                docs.append({
                    "name": file,
                    "rel_path": rel_path,
                    "owner": owner
                })

    docs_without_owner = [d for d in docs if not d["owner"]]

    # 7. Make Targets
    make_targets = []
    makefile_path = os.path.join(base_dir, "Makefile")
    if os.path.exists(makefile_path):
        try:
            with open(makefile_path, "r", encoding="utf-8") as f:
                for line in f:
                    match = re.match(r"^([a-zA-Z0-9_-]+):", line)
                    if match:
                        target = match.group(1)
                        if target not in (".PHONY", "DEFAULT_GOAL"):
                            make_targets.append(target)
        except Exception:
            pass

    # Ensure output directory exists
    output_dir = os.path.join(base_dir, "artifacts/complexity/latest")
    os.makedirs(output_dir, exist_ok=True)

    # 8. Generate recommendations list
    recommendations = []
    
    # R1: Duplicate scripts (safe cleanup)
    for dup_list in duplicate_scripts:
        original = dup_list[0]
        duplicates = dup_list[1:]
        recommendations.append({
            "target": f"Scripts duplicados: {', '.join([d['rel_path'] for d in duplicates])}",
            "type": "safe cleanup",
            "description": f"Os scripts acima são cópias idênticas de {original['rel_path']} (mesmo hash SHA-256). Podem ser removidos com segurança.",
            "impact": "Redução do número de scripts redundantes."
        })

    # R2: Legacy release-specific scripts (archive candidate)
    legacy_patterns = [r"v1\.5", r"v1\.6", r"v1\.7", r"v1\.8", r"cleanup-v", r"migration-v"]
    for s in scripts:
        for pattern in legacy_patterns:
            if re.search(pattern, s["name"]):
                recommendations.append({
                    "target": s["rel_path"],
                    "type": "archive candidate",
                    "description": f"Script de suporte/release antiga ({s['name']}). Fora do escopo do core estável v1.9.7.",
                    "impact": "Limpeza da pasta scripts/."
                })
                break

    # R3: Services without tests (needs coverage / deprecate candidate)
    for s in services_without_tests:
        # Check if the service file is imported anywhere in control_plane/
        imported = False
        try:
            # Simple grep simulation
            module_name = os.path.splitext(s["name"])[0]
            for r, d, files in os.walk(os.path.join(base_dir, "control_plane")):
                if "tests" in r:
                    continue
                for f in files:
                    if f.endswith(".py") and f != s["name"]:
                        with open(os.path.join(r, f), "r", encoding="utf-8") as handle:
                            content = handle.read()
                            if module_name in content:
                                imported = True
                                break
                if imported:
                    break
        except Exception:
            pass

        if not imported:
            recommendations.append({
                "target": s["rel_path"],
                "type": "deprecated candidate",
                "description": f"Serviço '{s['name']}' não possui arquivos de testes correspondentes e não parece ser importado no restante do código principal.",
                "impact": "Remoção de arquivo morto."
            })
        else:
            recommendations.append({
                "target": s["rel_path"],
                "type": "needs compatibility shim",
                "description": f"Serviço ativo '{s['name']}' não tem testes unitários nem de integração.",
                "impact": "Garantia de estabilidade e segurança."
            })

    # R4: Deprecated Endpoints (deprecated candidate / needs compatibility shim)
    for ep in deprecated_endpoints:
        recommendations.append({
            "target": f"Endpoint '{ep['method']} {ep['func_name']}' no router {ep['router']}",
            "type": "needs compatibility shim",
            "description": "Endpoint marcado oficialmente como deprecated no código. Deve ser mantido ativo para compatibilidade legada, mas monitorado para remoção futura.",
            "impact": "Limpeza futura da área de superfície da API."
        })

    # R5: Deprecated / Orphaned feature flags
    for flag_name in orphans:
        recommendations.append({
            "target": f"Feature Flag órfã: {flag_name}",
            "type": "safe cleanup",
            "description": "A flag está registrada no YAML de governança mas não é mais referenciada no código Python ou variáveis de ambiente. Pode ser removida com segurança.",
            "impact": "Estabilização e remoção de flags mortas."
        })
        
    for ff in deprecated_flags:
        recommendations.append({
            "target": f"Feature Flag deprecada: {ff['name']}",
            "type": "deprecated candidate",
            "description": "Flag de governança com status 'deprecated'. Planejar remoção definitiva.",
            "impact": "Redução do drift de configuração."
        })

    # R6: Docs without owners (needs owner assignment)
    for d in docs_without_owner:
        recommendations.append({
            "target": d["rel_path"],
            "type": "needs compatibility shim",
            "description": "Documento markdown sem declaração de 'owner:' no topo. Necessita de owner atribuído para governança de documentação.",
            "impact": "Conformidade com o framework de governança documental."
        })

    # Write files
    
    # 1. summary.md
    with open(os.path.join(output_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(f"""# Complexity Summary Report

Este relatório sumariza a complexidade estática do repositório `llm-inference-stack` com base em escaneamento estático de código, scripts, targets, feature flags e documentação.

## Métricas Gerais

| Métrica | Valor |
| --- | --- |
| Número de Routers | {len(routers)} |
| Número de Endpoints | {len(endpoints)} |
| Número de Services | {len(services)} |
| Número de Models (arquivos) | {len(models)} |
| Número de Scripts | {len(scripts)} |
| Número de Feature Flags | {len(feature_flags)} |
| Número de Documentos | {len(docs)} |
| Número de Make Targets | {len(make_targets)} |
| Endpoints Deprecados | {len(deprecated_endpoints)} |
| Endpoints Internos | {len(internal_endpoints)} |
| Scripts Duplicados (arquivos) | {sum(len(dup) for dup in duplicate_scripts)} |
| Services sem Testes | {len(services_without_tests)} |
| Documentos sem Owner | {len(docs_without_owner)} |

## Próximos Passos
Consulte os relatórios detalhados específicos de cada área:
- [API Surface](api-surface.md)
- [Services](services.md)
- [Models](models.md)
- [Scripts](scripts.md)
- [Feature Flags](feature-flags.md)
- [Recommendations](recommendations.md)
""")

    # 2. api-surface.md
    with open(os.path.join(output_dir, "api-surface.md"), "w", encoding="utf-8") as f:
        f.write("# API Surface Complexity Details\n\n")
        f.write(f"- **Total Routers**: {len(routers)}\n")
        f.write(f"- **Total Endpoints**: {len(endpoints)}\n")
        f.write(f"- **Deprecated Endpoints**: {len(deprecated_endpoints)}\n")
        f.write(f"- **Internal Endpoints**: {len(internal_endpoints)}\n\n")
        f.write("## Routers List\n\n")
        f.write("| Router File | Endpoints Count |\n| --- | --- |\n")
        for r in routers:
            f.write(f"| [{r['name']}](file://{r['path']}) | {r['endpoints_count']} |\n")
        f.write("\n## Deprecated Endpoints\n\n")
        if deprecated_endpoints:
            f.write("| Router | Method | Function Name |\n| --- | --- | --- |\n")
            for ep in deprecated_endpoints:
                f.write(f"| {ep['router']} | {ep['method']} | `{ep['func_name']}` |\n")
        else:
            f.write("Nenhum endpoint deprecado encontrado.\n")

    # 3. services.md
    with open(os.path.join(output_dir, "services.md"), "w", encoding="utf-8") as f:
        f.write("# Services Complexity Details\n\n")
        f.write(f"- **Total Services**: {len(services)}\n")
        f.write(f"- **Services sem Testes**: {len(services_without_tests)}\n\n")
        f.write("## Services List\n\n")
        f.write("| Service File | Classes | Methods | Has Tests? |\n| --- | --- | --- | --- |\n")
        for s in services:
            test_status = "✅ Yes" if s["has_tests"] else "❌ No"
            f.write(f"| [{s['name']}](file://{s['abs_path']}) | {s['classes_count']} | {s['methods_count']} | {test_status} |\n")

    # 4. models.md
    with open(os.path.join(output_dir, "models.md"), "w", encoding="utf-8") as f:
        f.write("# Models Complexity Details\n\n")
        f.write(f"- **Total Model Files**: {len(models)}\n\n")
        f.write("## SQLAlchemy Models Map\n\n")
        f.write("| Model File | Classes Identificadas |\n| --- | --- |\n")
        for m in models:
            classes_str = ", ".join([f"`{c}`" for c in m["classes"]]) if m["classes"] else "*Nenhuma*"
            f.write(f"| {m['name']} | {classes_str} |\n")

    # 5. scripts.md
    with open(os.path.join(output_dir, "scripts.md"), "w", encoding="utf-8") as f:
        f.write("# Scripts Complexity Details\n\n")
        f.write(f"- **Total Scripts**: {len(scripts)}\n")
        f.write(f"- **Total Duplicates Group**: {len(duplicate_scripts)}\n\n")
        f.write("## Duplicate Scripts Report\n\n")
        if duplicate_scripts:
            for idx, dup_list in enumerate(duplicate_scripts):
                f.write(f"### Grupo de Duplicação #{idx + 1}\n")
                f.write(f"- **Hash SHA-256**: `{dup_list[0]['sha']}`\n")
                f.write("- **Arquivos Identificados**:\n")
                for dup in dup_list:
                    f.write(f"  - [{dup['rel_path']}](file://{os.path.join(base_dir, dup['rel_path'])}) ({dup['size']} bytes)\n")
                f.write("\n")
        else:
            f.write("Nenhum script duplicado encontrado.\n")

    # 6. feature-flags.md
    with open(os.path.join(output_dir, "feature-flags.md"), "w", encoding="utf-8") as f:
        f.write("# Feature Flags Complexity Details\n\n")
        f.write(f"- **Total Registradas**: {len(feature_flags)}\n")
        f.write(f"- **Flags Órfãs**: {len(orphans)}\n")
        f.write(f"- **Flags Deprecadas**: {len(deprecated_flags)}\n\n")
        f.write("## Flags Órfãs List\n\n")
        if orphans:
            for o in sorted(orphans):
                f.write(f"- `{o}`\n")
        else:
            f.write("Nenhuma flag órfã detectada.\n")

    # 7. recommendations.md
    with open(os.path.join(output_dir, "recommendations.md"), "w", encoding="utf-8") as f:
        f.write("# Refactoring Recommendations Report\n\n")
        f.write("Abaixo estão listadas as recomendações formais de redução de complexidade classificadas por criticidade e impacto. Nenhuma remoção é feita automaticamente.\n\n")
        
        # Group by type
        types = ["safe cleanup", "needs compatibility shim", "deprecated candidate", "merge candidate", "archive candidate", "do not touch"]
        for t in types:
            matching_recs = [r for r in recommendations if r["type"] == t]
            f.write(f"## Classificação: `{t}`\n\n")
            if matching_recs:
                f.write("| Target | Recomendação / Descrição | Impacto Esperado |\n| --- | --- | --- |\n")
                for r in matching_recs:
                    f.write(f"| {r['target']} | {r['description']} | {r['impact']} |\n")
                f.write("\n")
            else:
                f.write("Nenhuma recomendação nesta categoria.\n\n")

    print("Success: Generated all complexity report markdown artifacts.")

if __name__ == "__main__":
    run_analysis()
