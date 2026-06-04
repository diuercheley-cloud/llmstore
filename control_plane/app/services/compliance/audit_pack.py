import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict

from app.core.time import utc_now
from app.models.commercial_compliance import (
    CommercialControlAttestation,
    CommercialOperationalEvidence,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AuditPackService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.base_path = Path("compliance/audit-packs")

    async def generate_pack(self, standard: str = "soc2") -> Dict[str, Any]:
        """
        Generates a structured audit pack for a given standard.
        """
        pack_id = uuid.uuid4()
        timestamp = utc_now().isoformat()
        pack_dir = self.base_path / standard / str(pack_id)
        os.makedirs(pack_dir, exist_ok=True)

        evidence_list = []
        
        # 1. Collect Operational Evidence
        op_evidence = list((await self.db.execute(select(CommercialOperationalEvidence))).scalars().all())
        for ev in op_evidence:
            data = {
                "id": str(ev.id),
                "type": ev.evidence_type,
                "title": ev.title,
                "summary": ev.summary,
                "collected_at": ev.collected_at.isoformat() if ev.collected_at else None,
                "content": self._sanitize_content(ev.evidence_json or {})
            }
            evidence_list.append(data)
            self._save_evidence_file(pack_dir, f"op_{ev.id}.json", data)

        # 2. Collect Attestations
        attestations = list((await self.db.execute(select(CommercialControlAttestation))).scalars().all())
        for att in attestations:
            data = {
                "id": str(att.id),
                "policy_id": str(att.control_policy_id),
                "attested_by": att.attested_by,
                "status": att.status,
                "period": f"{att.attestation_period_start} to {att.attestation_period_end}"
            }
            evidence_list.append(data)
            self._save_evidence_file(pack_dir, f"att_{att.id}.json", data)

        # 3. Create Manifest
        manifest = {
            "pack_id": str(pack_id),
            "standard": standard,
            "generated_at": timestamp,
            "evidence_count": len(evidence_list),
            "checksum": self._calculate_hash(evidence_list)
        }
        self._save_evidence_file(pack_dir, "manifest.json", manifest)

        return manifest

    def _sanitize_content(self, content: Any) -> Any:
        """
        Removes secrets and sensitive data from evidence.
        """
        if isinstance(content, dict):
            return {k: self._sanitize_content(v) for k, v in content.items() if not self._is_secret_key(k)}
        elif isinstance(content, list):
            return [self._sanitize_content(i) for i in content]
        return content

    def _is_secret_key(self, key: str) -> bool:
        secrets = ["api_key", "secret", "password", "token", "private_key"]
        return any(s in key.lower() for s in secrets)

    def _save_evidence_file(self, directory: Path, filename: str, content: Any):
        with open(directory / filename, "w") as f:
            json.dump(content, f, indent=2)

    def _calculate_hash(self, data: Any) -> str:
        s = json.dumps(data, sort_keys=True)
        return hashlib.sha256(s.encode()).hexdigest()
