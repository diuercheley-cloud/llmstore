import hashlib
import json
import os
import zipfile
from datetime import UTC, datetime
from typing import Any

from app.services.compliance_control_mapper import ComplianceControlMapperService
from sqlalchemy.ext.asyncio import AsyncSession


class ComplianceEvidenceCollectorService:
    def __init__(self, db: AsyncSession, base_artifact_dir: str = "artifacts/compliance/latest"):
        self.db = db
        self.base_artifact_dir = base_artifact_dir
        os.makedirs(self.base_artifact_dir, exist_ok=True)
        self.mapper = ComplianceControlMapperService()

    async def collect_all(self) -> dict[str, Any]:
        results = []
        controls = self.mapper.list_controls()

        # Evidence sources simulation
        sources = {
            "RBAC": "control_plane/app/api/dependencies.py",
            "Release Gate": "scripts/release-gate.sh",
            "Chaos": "docs/chaos/chaos-engineering.md",
            "SBOM": "artifacts/releases/v1.9.6-ci-chaos/python-sbom.txt",
            "Security": "artifacts/security-reports/latest/security-report.md",
        }

        evidence_index = []

        for source_name, path in sources.items():
            if os.path.exists(path):
                content = self._read_and_sanitize(path)
                file_hash = hashlib.sha256(content.encode()).hexdigest()

                # Create file in latest compliance dir
                target_filename = f"{source_name.lower().replace(' ', '_')}_{file_hash[:8]}.txt"
                target_path = os.path.join(self.base_artifact_dir, target_filename)

                with open(target_path, "w") as f:
                    f.write(content)

                evidence_index.append(
                    {
                        "source": source_name,
                        "original_path": path,
                        "collected_at": datetime.now(UTC).isoformat(),
                        "hash_sha256": file_hash,
                        "artifact": target_filename,
                    }
                )

        # Save index
        index_path = os.path.join(self.base_artifact_dir, "evidence-index.json")
        with open(index_path, "w") as f:
            json.dump(evidence_index, f, indent=2)

        return {"status": "success", "collected_count": len(evidence_index), "index": index_path}

    def _read_and_sanitize(self, path: str) -> str:
        with open(path, errors="ignore") as f:
            content = f.read()

        # Strict Sanitization Logic
        sensitive_patterns = [
            "PRIVATE KEY",
            "API_KEY",
            "SECRET",
            "PASSWORD",
            "TOKEN",
            "prompt",
            "completion",
            "document",
            "RAG",  # Sensitive AI terms in evidence context
        ]

        sanitized = content
        for pattern in sensitive_patterns:
            # Case insensitive replace with [REDACTED]
            import re

            sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

        return sanitized

    async def generate_package(self) -> str:
        zip_path = os.path.join(self.base_artifact_dir, "audit-package.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.base_artifact_dir):
                for file in files:
                    if file != "audit-package.zip":
                        zipf.write(os.path.join(root, file), file)
        return zip_path
