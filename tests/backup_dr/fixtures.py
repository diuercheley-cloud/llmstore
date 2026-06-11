from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas.backup import BackupManifest
from app.services.backup.backup_service import BackupService, _sha256_bytes

def _rewrite_backup_for_path_traversal(service: BackupService, backup_store_root: Path, backup_id: str) -> None:
    manifest = service._read_manifest(backup_id)
    backup_dir = backup_store_root / "system" / backup_id
    payload_path = backup_dir / "payload.tar.gz.enc"
    
    archive_bytes = service.crypto.decrypt(payload_path.read_bytes())
    from app.services.backup.archive import ArchiveReader, ArchiveService
    parts = ArchiveReader.extract(archive_bytes)
    
    # Inject traversal
    if "configs.json" in parts:
        configs = parts["configs.json"]
        if isinstance(configs, bytes):
            configs = json.loads(configs)
            
        if configs.get("files"):
            configs["files"][0]["path"] = "../escape.txt"
        parts["configs.json"] = json.dumps(configs, sort_keys=True).encode("utf-8")
        
    # Re-serialize all parts to bytes for ArchiveService.create
    bytes_parts = {}
    for k, v in parts.items():
        if isinstance(v, dict):
            bytes_parts[k] = json.dumps(v, sort_keys=True).encode("utf-8")
        else:
            bytes_parts[k] = v

    archive_bytes = ArchiveService().create(bytes_parts)
    encrypted_payload = service.crypto.encrypt(archive_bytes)
    payload_path.write_bytes(encrypted_payload)

    for component in manifest.components:
        payload = bytes_parts.get(component.file_name)
        if payload:
            component.data_hash = _sha256_bytes(payload)
            
    manifest.archive_checksum = _sha256_bytes(encrypted_payload)
    manifest.payload_signature = service.crypto.sign_payload(
        {
            "backup_id": manifest.backup_id,
            "archive_checksum": manifest.archive_checksum,
            "components": [component.model_dump() for component in manifest.components],
        }
    )
    
    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json(), encoding="utf-8")

# Re-exporting fixtures from parent to avoid duplication but adding helper
from tests.backup.fixtures import RecoveryIds, seed_recovery_state, collect_recovery_state, mutate_recovery_state, prepare_repo_tree
