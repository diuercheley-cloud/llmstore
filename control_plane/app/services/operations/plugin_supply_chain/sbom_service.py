import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List
import uuid

from app.models.operations.plugin_supply_chain import PluginSBOMPlaceholder
from app.services.operations.plugin_supply_chain.hash_utils import compute_sbom_hash, sha256_hex
from app.utils.crypto_signer import verify_signature

class SBOMGenerationError(RuntimeError):
    pass

class PluginSBOMService:
    def calculate_package_hash(self, plugin_path: Path) -> str:
        file_hashes = {}
        for root, _, files in os.walk(plugin_path):
            for file in sorted(files):
                rel_path = os.path.relpath(os.path.join(root, file), plugin_path)
                parts = rel_path.split(os.sep)
                # Skip common ignored directories/files
                if any(part in parts for part in [".git", "__pycache__", ".venv", "node_modules"]):
                    continue
                
                filepath = Path(root) / file
                
                # Check for critical unexpected files:
                # - env files (.env, etc.)
                # - credentials / private keys (.pem, .key, etc.)
                # - binary libraries / executables (.exe, .dll, .so, .dylib, .bin)
                lower_file = file.lower()
                is_unexpected = False
                
                if file.startswith(".env") or lower_file == ".env":
                    is_unexpected = True
                elif any(pattern in lower_file for pattern in [".pem", ".key", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"]):
                    is_unexpected = True
                elif any(lower_file.endswith(ext) for ext in [".exe", ".dll", ".so", ".dylib", ".bin"]):
                    is_unexpected = True
                    
                if is_unexpected:
                    raise SBOMGenerationError(f"Critical unexpected file found: {rel_path}")
                
                hasher = hashlib.sha256()
                try:
                    with open(filepath, "rb") as f:
                        while chunk := f.read(8192):
                            hasher.update(chunk)
                except Exception as e:
                    raise SBOMGenerationError(f"Failed to read file {rel_path} for hashing: {e}")
                
                file_hashes[rel_path] = hasher.hexdigest()
        
        if not file_hashes:
            raise SBOMGenerationError("No package files found to calculate hash.")
            
        return sha256_hex(file_hashes)

    def _parse_dependency_string(self, dep: str) -> tuple[str, str]:
        operators = ["==", ">=", "<=", "~=", ">", "<"]
        for op in operators:
            if op in dep:
                parts = dep.split(op)
                return parts[0].strip(), op + parts[1].strip()
        return dep.strip(), "unknown"

    def generate_sbom(
        self,
        provenance_record: Any,
        plugin_path: Path,
        expected_hash: str | None = None,
        signature: str | None = None,
        reproducible_build: bool = True,
        offline_verifiable: bool = True,
    ) -> PluginSBOMPlaceholder:
        
        if not plugin_path.exists() or not plugin_path.is_dir():
            raise SBOMGenerationError(f"Plugin path does not exist or is not a directory: {plugin_path}")
            
        # 4. Calcular hashes dos arquivos do pacote.
        package_hash = self.calculate_package_hash(plugin_path)
        
        # 5. Validar integridade:
        # - hash esperado vs hash real
        if expected_hash and expected_hash != package_hash:
            raise SBOMGenerationError(f"Integrity check failed: expected hash {expected_hash}, got {package_hash}")
            
        # - assinatura, se disponível
        if signature:
            if not verify_signature(package_hash, signature):
                raise SBOMGenerationError("Integrity check failed: signature verification failed")
                
        # 2. Gerar SBOM real para plugin
        name = None
        version = None
        dep_map = {}
        licenses = []
        
        pyproject_path = plugin_path / "pyproject.toml"
        requirements_path = plugin_path / "requirements.txt"
        package_json_path = plugin_path / "package.json"
        package_lock_path = plugin_path / "package-lock.json"
        
        has_python = pyproject_path.exists() or requirements_path.exists()
        has_node = package_json_path.exists() or package_lock_path.exists()
        
        if not has_python and not has_node:
            raise SBOMGenerationError("Neither Python (pyproject.toml/requirements.txt) nor Node (package.json/package-lock.json) files were found.")
            
        if pyproject_path.exists():
            import tomllib
            try:
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                    project = data.get("project", {})
                    name = project.get("name")
                    version = project.get("version")
                    for dep in project.get("dependencies", []):
                        dep_name, dep_version = self._parse_dependency_string(dep)
                        dep_map[dep_name] = dep_version
                    
                    license_val = project.get("license")
                    if isinstance(license_val, dict):
                        if "text" in license_val:
                            licenses.append(license_val["text"])
                        elif "file" in license_val:
                            licenses.append(f"File: {license_val['file']}")
                    elif isinstance(license_val, str):
                        licenses.append(license_val)
            except Exception as e:
                raise SBOMGenerationError(f"Failed to parse pyproject.toml: {e}")
                
        if requirements_path.exists():
            try:
                with open(requirements_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        dep_name, dep_version = self._parse_dependency_string(line)
                        dep_map[dep_name] = dep_version
            except Exception as e:
                raise SBOMGenerationError(f"Failed to parse requirements.txt: {e}")
                
        if package_json_path.exists():
            try:
                with open(package_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    name = name or data.get("name")
                    version = version or data.get("version")
                    
                    node_deps = data.get("dependencies", {})
                    node_dev_deps = data.get("devDependencies", {})
                    for dep_name, dep_ver in {**node_deps, **node_dev_deps}.items():
                        dep_map[dep_name] = dep_ver
                        
                    license_val = data.get("license")
                    if license_val:
                        if isinstance(license_val, dict) and "type" in license_val:
                            licenses.append(license_val["type"])
                        elif isinstance(license_val, str):
                            licenses.append(license_val)
            except Exception as e:
                raise SBOMGenerationError(f"Failed to parse package.json: {e}")
                
        if package_lock_path.exists():
            try:
                with open(package_lock_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    packages = data.get("packages", {})
                    if packages:
                        for pkg_name, pkg_data in packages.items():
                            if not pkg_name:
                                continue
                            clean_pkg_name = pkg_name.replace("node_modules/", "")
                            pkg_version = pkg_data.get("version")
                            if pkg_version:
                                dep_map[clean_pkg_name] = pkg_version
                    else:
                        node_deps = data.get("dependencies", {})
                        for dep_name, dep_data in node_deps.items():
                            dep_version = dep_data.get("version")
                            if dep_version:
                                dep_map[dep_name] = dep_version
            except Exception as e:
                raise SBOMGenerationError(f"Failed to parse package-lock.json: {e}")
                
        if not licenses:
            try:
                for file in os.listdir(plugin_path):
                    if file.upper() in ["LICENSE", "LICENSE.TXT", "LICENSE.MD", "COPYING"]:
                        content = (plugin_path / file).read_text(errors="ignore")
                        if "MIT" in content:
                            licenses.append("MIT")
                        elif "Apache" in content:
                            licenses.append("Apache-2.0")
                        elif "GPL" in content:
                            licenses.append("GPL")
                        elif "BSD" in content:
                            licenses.append("BSD")
                        else:
                            licenses.append("Proprietary")
                        break
            except Exception:
                pass
                
        name = name or provenance_record.artifact_name or "unknown-plugin"
        version = version or provenance_record.artifact_version or "0.0.0"
        
        bom_uuid = str(uuid.uuid4())
        components = []
        for dep_name, dep_version in sorted(dep_map.items()):
            clean_ver = dep_version
            for op in ["==", ">=", "<=", "~=", ">", "<", "^"]:
                if clean_ver.startswith(op):
                    clean_ver = clean_ver[len(op):]
            components.append({
                "type": "library",
                "name": dep_name,
                "version": clean_ver
            })
            
        cyclonedx_sbom = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "serialNumber": f"urn:uuid:{bom_uuid}",
            "version": 1,
            "metadata": {
                "component": {
                    "type": "application",
                    "name": name,
                    "version": version,
                    "hashes": [
                        {
                            "alg": "SHA-256",
                            "content": package_hash
                        }
                    ],
                    "licenses": [
                        {"license": {"id": lic}} for lic in licenses
                    ] if licenses else []
                }
            },
            "components": components
        }
        
        logical_payload = {
            "client_id": str(provenance_record.client_id),
            "provenance_record_id": provenance_record.id,
            "sbom_format": "cyclonedx_json",
            "dependency_summary_json": cyclonedx_sbom,
            "denied_dependencies_json": [],
            "reproducible_build": reproducible_build,
            "offline_verifiable": offline_verifiable,
        }
        
        sbom_hash = compute_sbom_hash(logical_payload)
        immutable_hash = sha256_hex({"kind": "plugin_supply_chain_sbom_immutable", "sbom_hash": sbom_hash})
        
        sbom_record = PluginSBOMPlaceholder(
            id=sha256_hex({"kind": "plugin_supply_chain_sbom_id", **logical_payload}),
            client_id=provenance_record.client_id,
            provenance_record_id=provenance_record.id,
            sbom_format="cyclonedx_json",
            dependency_summary_json=cyclonedx_sbom,
            denied_dependencies_json=[],
            reproducible_build=reproducible_build,
            offline_verifiable=offline_verifiable,
            sbom_hash=sbom_hash,
            immutable_hash=immutable_hash,
        )
        sbom_record._logical_payload = logical_payload
        return sbom_record

    def validate_sbom(
        self,
        sbom_record: PluginSBOMPlaceholder,
        expected_hash: str | None = None,
        signature: str | None = None,
    ) -> dict[str, Any]:
        
        logical_payload = getattr(sbom_record, "_logical_payload", None) or {
            "client_id": str(sbom_record.client_id),
            "provenance_record_id": sbom_record.provenance_record_id,
            "sbom_format": sbom_record.sbom_format,
            "dependency_summary_json": sbom_record.dependency_summary_json,
            "denied_dependencies_json": sbom_record.denied_dependencies_json,
            "reproducible_build": sbom_record.reproducible_build,
            "offline_verifiable": sbom_record.offline_verifiable,
        }
        replayed_hash = compute_sbom_hash(logical_payload)
        valid = replayed_hash == sbom_record.sbom_hash
        
        package_hash = None
        try:
            package_hash = sbom_record.dependency_summary_json["metadata"]["component"]["hashes"][0]["content"]
        except (KeyError, IndexError):
            pass
            
        if expected_hash and package_hash and expected_hash != package_hash:
            valid = False
            
        if signature and package_hash:
            if not verify_signature(package_hash, signature):
                valid = False
                
        return {
            "valid": valid,
            "signature_only": True if not signature else False,
            "offline_verifiable": sbom_record.offline_verifiable,
            "reproducible_build": sbom_record.reproducible_build,
            "original_hash": sbom_record.sbom_hash,
            "replayed_hash": replayed_hash,
        }

    def explain_sbom(self, sbom_record: PluginSBOMPlaceholder) -> dict[str, Any]:
        return {
            "sbom_format": sbom_record.sbom_format,
            "signature_only": False,
            "formal_sbom": True,
            "offline_verifiable": sbom_record.offline_verifiable,
            "reproducible_build": sbom_record.reproducible_build,
            "notes": [
                "CycloneDX JSON SBOM generated",
                "integrity validated dynamically",
                "package hash computed and stored",
            ],
        }
